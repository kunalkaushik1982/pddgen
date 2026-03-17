r"""
Purpose: Background draft-generation coordinator for transcript normalization and screenshot derivation.
Full filepath: C:\Users\work\Documents\PddGenerator\worker\services\draft_generation_worker.py
"""

import json
from pathlib import Path
import re
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from worker.bootstrap import get_backend_settings, get_db_session
from worker.services.ai_transcript_interpreter import AITranscriptInterpreter
from worker.services.transcript_normalizer import TranscriptNormalizer
from worker.services.video_frame_extractor import ExtractedFrameCandidate, VideoFrameExtractor

from app.models.artifact import ArtifactModel
from app.models.action_log import ActionLogModel
from app.models.draft_session import DraftSessionModel
from app.models.process_note import ProcessNoteModel
from app.models.process_step import ProcessStepModel
from app.models.process_step_screenshot_candidate import ProcessStepScreenshotCandidateModel
from app.models.process_step_screenshot import ProcessStepScreenshotModel
from app.services.action_log_service import ActionLogService
from app.services.step_extraction import StepExtractionService
from app.services.transcript_intelligence import TranscriptIntelligenceService

TIMESTAMP_PATTERN = re.compile(r"\b(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\b")
ACTION_VERB_PATTERNS = {
    "navigate": ("open", "navigate", "launch", "go to", "switch to", "login", "log in"),
    "data_entry": ("enter", "paste", "type", "update", "fill", "input"),
    "copy": ("copy",),
    "submit": ("submit", "save", "confirm", "create", "send"),
}
ACTION_OFFSET_WINDOWS = {
    "navigate": [0, 1, 2, 3, 4, -1, -2],
    "data_entry": [-1, 0, 1, 2, 3, -2],
    "copy": [-2, -1, 0, 1],
    "submit": [1, 2, 3, 4, 0, -1],
    "default": [-2, -1, 0, 1, 2, 3],
}
SCREENSHOT_ROLE_ORDER = ("before", "during", "after")
SCREENSHOT_ROLE_LOCAL_OFFSETS = {
    "before": [-1, 0, 1],
    "during": [-1, 0, 1],
    "after": [0, 1, 2],
}


class DraftGenerationWorker:
    """Run transcript normalization and derived screenshot extraction in the background."""

    def __init__(self) -> None:
        self.settings = get_backend_settings()
        self.ai_transcript_interpreter = AITranscriptInterpreter()
        self.transcript_normalizer = TranscriptNormalizer()
        self.step_extractor = StepExtractionService()
        self.note_extractor = TranscriptIntelligenceService()
        self.frame_extractor = VideoFrameExtractor()
        self.action_log_service = ActionLogService()

    def run(self, session_id: str) -> dict[str, int | str]:
        """Generate draft steps, notes, and derived screenshots for a session."""
        db = get_db_session()
        try:
            session = self._load_session(db, session_id)
            session.status = "processing"
            db.commit()

            transcript_artifacts = [artifact for artifact in session.artifacts if artifact.kind == "transcript"]
            video_artifacts = [artifact for artifact in session.artifacts if artifact.kind == "video"]
            if not transcript_artifacts:
                raise ValueError("No transcript artifacts found for draft generation.")

            step_ids_subquery = select(ProcessStepModel.id).where(ProcessStepModel.session_id == session_id)
            db.execute(delete(ProcessStepScreenshotModel).where(ProcessStepScreenshotModel.step_id.in_(step_ids_subquery)))
            db.execute(
                delete(ProcessStepScreenshotCandidateModel).where(
                    ProcessStepScreenshotCandidateModel.step_id.in_(step_ids_subquery)
                )
            )
            db.execute(delete(ProcessStepModel).where(ProcessStepModel.session_id == session_id))
            db.execute(delete(ProcessNoteModel).where(ProcessNoteModel.session_id == session_id))
            db.execute(
                delete(ArtifactModel).where(
                    ArtifactModel.session_id == session_id,
                    ArtifactModel.kind == "screenshot",
                )
            )
            db.commit()

            all_steps: list[dict] = []
            all_notes: list[dict] = []
            steps_by_transcript: dict[str, list[dict]] = {}
            self._record_stage(
                db,
                session_id,
                "Interpreting transcript",
                f"Processing {len(transcript_artifacts)} transcript artifact(s).",
            )
            for transcript in transcript_artifacts:
                normalized_text = self.transcript_normalizer.normalize(transcript.storage_path, transcript.name)
                interpretation = self.ai_transcript_interpreter.interpret(
                    transcript_artifact_id=transcript.id,
                    transcript_text=normalized_text,
                )

                if interpretation is not None and interpretation.steps:
                    self._ground_ai_step_spans(interpretation.steps, normalized_text)
                    all_steps.extend(interpretation.steps)
                    steps_by_transcript.setdefault(transcript.id, []).extend(interpretation.steps)
                    all_notes.extend(interpretation.notes)
                    continue

                transcript_steps = self.step_extractor.extract_steps(
                    transcript_artifact_id=transcript.id,
                    transcript_text=normalized_text,
                )
                all_steps.extend(transcript_steps)
                steps_by_transcript.setdefault(transcript.id, []).extend(transcript_steps)
                all_notes.extend(
                    self.note_extractor.extract_notes(
                        transcript_artifact_id=transcript.id,
                        transcript_text=normalized_text,
                    )
                )

            for step_number, step in enumerate(all_steps, start=1):
                step["step_number"] = step_number

            screenshot_artifacts: list[ArtifactModel] = []
            if video_artifacts:
                self._record_stage(
                    db,
                    session_id,
                    "Extracting screenshots",
                    self._build_pairing_detail(transcript_artifacts, video_artifacts),
                )
                for transcript_index, transcript in enumerate(transcript_artifacts):
                    transcript_steps = steps_by_transcript.get(transcript.id, [])
                    if not transcript_steps:
                        continue
                    paired_video = video_artifacts[min(transcript_index, len(video_artifacts) - 1)]
                    screenshot_artifacts.extend(
                        self._derive_screenshots(
                            db=db,
                            session_id=session_id,
                            video_artifacts=[paired_video],
                            step_candidates=transcript_steps,
                        )
                    )

            self._record_stage(db, session_id, "Building diagram", "Generating the session diagram model.")
            diagram_interpretation = None
            try:
                diagram_interpretation = self.ai_transcript_interpreter.interpret_diagrams(
                    session_title=session.title,
                    diagram_type=session.diagram_type,
                    steps=all_steps,
                    notes=all_notes,
                )
            except Exception:
                diagram_interpretation = None

            if diagram_interpretation is not None:
                session.overview_diagram_json = json.dumps(diagram_interpretation.overview)
                session.detailed_diagram_json = json.dumps(diagram_interpretation.detailed)
            else:
                session.overview_diagram_json = ""
                session.detailed_diagram_json = ""

            step_models = [ProcessStepModel(session_id=session_id, **self._to_step_record(step)) for step in all_steps]
            db.add_all(step_models)
            db.flush()
            self._persist_step_screenshots(db, step_models, all_steps)
            db.add_all(ProcessNoteModel(session_id=session_id, **note) for note in all_notes)
            session.status = "review"
            db.add(
                ActionLogModel(
                    session_id=session_id,
                    event_type="draft_generated",
                    title="Ready for review",
                    detail=f"{len(all_steps)} steps, {len(all_notes)} notes, {len(screenshot_artifacts)} screenshots.",
                    actor="system",
                )
            )
            db.commit()

            return {
                "session_id": session_id,
                "steps_created": len(all_steps),
                "notes_created": len(all_notes),
                "screenshots_created": len(screenshot_artifacts),
            }
        except Exception as exc:
            self._mark_failed(db, session_id, str(exc))
            raise
        finally:
            db.close()

    def _load_session(self, db, session_id: str) -> DraftSessionModel:
        statement = (
            select(DraftSessionModel)
            .where(DraftSessionModel.id == session_id)
            .options(
                selectinload(DraftSessionModel.artifacts),
                selectinload(DraftSessionModel.process_steps),
                selectinload(DraftSessionModel.process_notes),
            )
        )
        session = db.execute(statement).scalar_one_or_none()
        if session is None:
            raise ValueError(f"Draft session '{session_id}' was not found.")
        return session

    def _derive_screenshots(self, *, db, session_id: str, video_artifacts: list[ArtifactModel], step_candidates: list[dict]) -> list[ArtifactModel]:
        if not video_artifacts or not self.frame_extractor.is_available():
            return []

        primary_video = video_artifacts[0]
        screenshots: list[ArtifactModel] = []
        screenshots_dir = self.settings.local_storage_root / session_id / "generated-screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)

        for step in step_candidates:
            candidate_screenshots = self._derive_candidate_screenshot_pool(
                db=db,
                session_id=session_id,
                video_path=primary_video.storage_path,
                screenshots_dir=screenshots_dir,
                step=step,
            )
            if not candidate_screenshots:
                continue

            derived_screenshots = self._select_step_screenshot_slots(
                step=step,
                candidate_screenshots=candidate_screenshots,
            )
            step["_candidate_screenshots"] = candidate_screenshots
            step["_derived_screenshots"] = derived_screenshots
            primary_screenshot = next((item for item in derived_screenshots if item["is_primary"]), derived_screenshots[0])
            step["screenshot_id"] = primary_screenshot["artifact"].id
            step["timestamp"] = primary_screenshot["timestamp"]
            screenshots.extend(item["artifact"] for item in candidate_screenshots)
        db.commit()
        return screenshots

    @staticmethod
    def _attach_screenshot_evidence(step: dict) -> None:
        """Append screenshot evidence references to the step payload."""
        derived_screenshots = step.get("_derived_screenshots", [])
        if not derived_screenshots:
            return
        evidence_references = json.loads(step["evidence_references"])
        for screenshot in derived_screenshots:
            evidence_references.append(
                {
                    "id": str(uuid4()),
                    "artifact_id": screenshot["artifact"].id,
                    "kind": "screenshot",
                    "locator": screenshot["timestamp"] or step.get("timestamp") or f"step:{step['step_number']}",
                }
            )
        step["evidence_references"] = json.dumps(evidence_references)

    def _persist_step_screenshots(self, db, step_models: list[ProcessStepModel], step_candidates: list[dict]) -> None:
        """Persist screenshot relations after step rows exist."""
        relations: list[ProcessStepScreenshotModel] = []
        candidate_relations: list[ProcessStepScreenshotCandidateModel] = []
        for step_model, step_candidate in zip(step_models, step_candidates):
            self._attach_screenshot_evidence(step_candidate)
            step_model.evidence_references = step_candidate["evidence_references"]
            step_model.screenshot_id = step_candidate.get("screenshot_id", "")
            step_model.timestamp = step_candidate.get("timestamp", "")
            for candidate in step_candidate.get("_candidate_screenshots", []):
                candidate_relations.append(
                    ProcessStepScreenshotCandidateModel(
                        step_id=step_model.id,
                        artifact_id=candidate["artifact"].id,
                        sequence_number=candidate["sequence_number"],
                        timestamp=candidate["timestamp"],
                        source_role=candidate["source_role"],
                        selection_method=candidate["selection_method"],
                    )
                )
            for screenshot in step_candidate.get("_derived_screenshots", []):
                relations.append(
                    ProcessStepScreenshotModel(
                        step_id=step_model.id,
                        artifact_id=screenshot["artifact"].id,
                        role=screenshot["role"],
                        sequence_number=screenshot["sequence_number"],
                        timestamp=screenshot["timestamp"],
                        selection_method=screenshot["selection_method"],
                        is_primary=screenshot["is_primary"],
                    )
                )
        if candidate_relations:
            db.add_all(candidate_relations)
        if relations:
            db.add_all(relations)

    @staticmethod
    def _to_step_record(step: dict) -> dict:
        """Strip worker-only fields before persisting a process step."""
        return {
            key: value
            for key, value in step.items()
            if key
            not in {
                "_candidate_screenshots",
                "_derived_screenshots",
            }
        }

    @staticmethod
    def _extract_transcript_timestamps(transcript_text: str) -> list[str]:
        """Extract normalized timestamps from transcript text in source order."""
        timestamps: list[str] = []
        for match in TIMESTAMP_PATTERN.finditer(transcript_text):
            hours_group, minutes_group, seconds_group = match.groups()
            hours = int(hours_group or 0)
            minutes = int(minutes_group)
            seconds = int(seconds_group)
            timestamps.append(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        return timestamps

    def _ground_ai_step_spans(self, step_candidates: list[dict], transcript_text: str) -> None:
        """Backfill missing AI timestamps and evidence spans from transcript order."""
        transcript_timestamps = self._extract_transcript_timestamps(transcript_text)
        if not transcript_timestamps:
            return

        for index, step in enumerate(step_candidates):
            inferred_start = transcript_timestamps[index] if index < len(transcript_timestamps) else transcript_timestamps[-1]
            inferred_end = (
                transcript_timestamps[index + 1]
                if (index + 1) < len(transcript_timestamps)
                else inferred_start
            )

            if not str(step.get("start_timestamp", "") or ""):
                step["start_timestamp"] = inferred_start
            if not str(step.get("end_timestamp", "") or ""):
                step["end_timestamp"] = inferred_end
            if not str(step.get("timestamp", "") or ""):
                step["timestamp"] = step["start_timestamp"]
            if not str(step.get("supporting_transcript_text", "") or ""):
                step["supporting_transcript_text"] = step.get("action_text", "")

            if self._timestamp_to_seconds(step["end_timestamp"]) < self._timestamp_to_seconds(step["start_timestamp"]):
                step["end_timestamp"] = step["start_timestamp"]

    def _build_candidate_offsets(self, step: dict) -> list[int]:
        """Return candidate frame offsets based on inferred action type and timestamp confidence."""
        action_type = self._classify_action_type(step.get("action_text", ""))
        offsets = ACTION_OFFSET_WINDOWS.get(action_type, ACTION_OFFSET_WINDOWS["default"])
        if step.get("confidence") in {"low", "unknown"}:
            widened = offsets + [-4, 4, -5, 5]
            # Preserve ordering while removing duplicates.
            seen: set[int] = set()
            ordered: list[int] = []
            for item in widened:
                if item in seen:
                    continue
                seen.add(item)
                ordered.append(item)
            return ordered
        return offsets

    def _build_candidate_timestamps(self, step: dict) -> list[str]:
        """Return ordered candidate timestamps from a grounded step span."""
        fallback_timestamp = step.get("timestamp") or "00:00:01"
        start_timestamp = step.get("start_timestamp") or fallback_timestamp
        end_timestamp = step.get("end_timestamp") or fallback_timestamp
        start_seconds = self._timestamp_to_seconds(start_timestamp)
        end_seconds = max(start_seconds, self._timestamp_to_seconds(end_timestamp))
        display_seconds = self._timestamp_to_seconds(fallback_timestamp)

        sample_points = list(range(start_seconds, end_seconds + 1))
        for offset in self._build_candidate_offsets(step):
            sample_points.append(max(1, display_seconds + offset))

        ordered_points: list[int] = []
        seen: set[int] = set()
        for point in sample_points:
            if point in seen:
                continue
            seen.add(point)
            ordered_points.append(point)
        return [self._seconds_to_timestamp(point) for point in ordered_points]

    def _derive_step_screenshot_slots(
        self,
        *,
        db,
        session_id: str,
        video_path: str,
        screenshots_dir: Path,
        step: dict,
    ) -> list[dict]:
        """Generate up to three screenshot slots for one step."""
        candidate_screenshots = self._derive_candidate_screenshot_pool(
            db=db,
            session_id=session_id,
            video_path=video_path,
            screenshots_dir=screenshots_dir,
            step=step,
        )
        return self._select_step_screenshot_slots(step=step, candidate_screenshots=candidate_screenshots)

    def _derive_candidate_screenshot_pool(
        self,
        *,
        db,
        session_id: str,
        video_path: str,
        screenshots_dir: Path,
        step: dict,
    ) -> list[dict]:
        """Generate a broader candidate pool that the BA can browse later."""
        candidate_timestamps = self._build_candidate_timestamps(step)
        extracted_candidates = self.frame_extractor.extract_frames_at_timestamps(
            video_path=video_path,
            output_dir=str(screenshots_dir),
            timestamps=candidate_timestamps,
            filename_prefix=f"step_{step['step_number']:03d}_candidate",
        )
        screenshot_candidates: list[dict] = []
        seen_timestamps: set[str] = set()
        for candidate in extracted_candidates:
            if candidate.timestamp in seen_timestamps:
                continue
            seen_timestamps.add(candidate.timestamp)
            artifact = ArtifactModel(
                session_id=session_id,
                name=Path(candidate.output_path).name,
                kind="screenshot",
                storage_path=str(candidate.output_path),
                content_type="image/png",
                size_bytes=candidate.file_size,
            )
            db.add(artifact)
            db.flush()
            screenshot_candidates.append(
                {
                    "artifact": artifact,
                    "sequence_number": len(screenshot_candidates) + 1,
                    "timestamp": candidate.timestamp,
                    "source_role": "candidate",
                    "selection_method": "span-candidate",
                    "offset_seconds": candidate.offset_seconds,
                    "file_size": candidate.file_size,
                }
            )
        return screenshot_candidates

    def _select_step_screenshot_slots(self, *, step: dict, candidate_screenshots: list[dict]) -> list[dict]:
        """Choose the selected screenshots from the broader candidate pool."""
        if not candidate_screenshots:
            return []

        roles = self._select_screenshot_roles(step)
        screenshots: list[dict] = []
        used_artifact_ids: set[str] = set()
        for sequence_number, role in enumerate(roles, start=1):
            target_timestamp = self._timestamp_for_role(step, role)
            candidate_timestamps = self._candidate_timestamps_for_role(target_timestamp, role)
            candidate_timestamp_set = set(candidate_timestamps)
            scoped_candidates = [
                candidate
                for candidate in candidate_screenshots
                if candidate["artifact"].id not in used_artifact_ids and candidate["timestamp"] in candidate_timestamp_set
            ]
            if not scoped_candidates:
                scoped_candidates = [
                    candidate for candidate in candidate_screenshots if candidate["artifact"].id not in used_artifact_ids
                ]

            best_candidate = self._select_best_candidate_record(step, scoped_candidates)
            if best_candidate is None:
                continue

            used_artifact_ids.add(best_candidate["artifact"].id)
            screenshots.append(
                {
                    "artifact": best_candidate["artifact"],
                    "role": role,
                    "sequence_number": sequence_number,
                    "timestamp": best_candidate["timestamp"],
                    "selection_method": "span-sequence",
                    "is_primary": role == "during" or (role == roles[0] and "during" not in roles),
                }
            )
        if screenshots and not any(item["is_primary"] for item in screenshots):
            screenshots[0]["is_primary"] = True
        return screenshots

    def _select_best_candidate_record(self, step: dict, candidates: list[dict]) -> dict | None:
        """Choose the best persisted candidate using the existing heuristic scoring."""
        if not candidates:
            return None

        action_type = self._classify_action_type(step.get("action_text", ""))
        best_candidate: dict | None = None
        best_score = float("-inf")
        for candidate in candidates:
            frame_candidate = ExtractedFrameCandidate(
                output_path=candidate["artifact"].storage_path,
                timestamp=candidate["timestamp"],
                offset_seconds=candidate.get("offset_seconds", 0),
                file_size=candidate.get("file_size", candidate["artifact"].size_bytes),
            )
            score = self._score_candidate(action_type, frame_candidate, step)
            if score > best_score:
                best_score = score
                best_candidate = candidate
        return best_candidate

    def _select_screenshot_roles(self, step: dict) -> list[str]:
        """Return ordered screenshot roles for one step."""
        span_seconds = max(
            0,
            self._timestamp_to_seconds(step.get("end_timestamp") or step.get("timestamp") or "00:00:01")
            - self._timestamp_to_seconds(step.get("start_timestamp") or step.get("timestamp") or "00:00:01"),
        )
        action_type = self._classify_action_type(step.get("action_text", ""))
        if span_seconds <= 2:
            return ["during"]
        if span_seconds <= 6:
            if action_type in {"navigate", "submit"}:
                return ["before", "after"]
            return ["during", "after"]
        return list(SCREENSHOT_ROLE_ORDER)

    def _timestamp_for_role(self, step: dict, role: str) -> str:
        """Choose the target timestamp for one screenshot role."""
        start_seconds = self._timestamp_to_seconds(step.get("start_timestamp") or step.get("timestamp") or "00:00:01")
        end_seconds = max(start_seconds, self._timestamp_to_seconds(step.get("end_timestamp") or step.get("timestamp") or "00:00:01"))
        if role == "before":
            return self._seconds_to_timestamp(start_seconds)
        if role == "after":
            return self._seconds_to_timestamp(end_seconds)
        midpoint = start_seconds + ((end_seconds - start_seconds) // 2)
        return self._seconds_to_timestamp(midpoint)

    def _candidate_timestamps_for_role(self, base_timestamp: str, role: str) -> list[str]:
        """Build local candidate timestamps around one role target."""
        base_seconds = self._timestamp_to_seconds(base_timestamp)
        offsets = SCREENSHOT_ROLE_LOCAL_OFFSETS.get(role, [0])
        points = [max(1, base_seconds + offset) for offset in offsets]
        ordered: list[int] = []
        seen: set[int] = set()
        for point in points:
            if point in seen:
                continue
            seen.add(point)
            ordered.append(point)
        return [self._seconds_to_timestamp(point) for point in ordered]

    @staticmethod
    def _classify_action_type(action_text: str) -> str:
        """Infer a coarse action type from step text."""
        lowered = action_text.lower()
        for action_type, patterns in ACTION_VERB_PATTERNS.items():
            if any(pattern in lowered for pattern in patterns):
                return action_type
        return "default"

    def _select_best_frame(self, step: dict, candidates: list[ExtractedFrameCandidate]) -> ExtractedFrameCandidate | None:
        """Choose the best candidate frame using heuristic scoring."""
        if not candidates:
            return None

        action_type = self._classify_action_type(step.get("action_text", ""))
        best_candidate: ExtractedFrameCandidate | None = None
        best_score = float("-inf")
        for candidate in candidates:
            score = self._score_candidate(action_type, candidate, step)
            if score > best_score:
                best_score = score
                best_candidate = candidate
        return best_candidate

    @staticmethod
    def _score_candidate(action_type: str, candidate: ExtractedFrameCandidate, step: dict) -> float:
        """Score one frame candidate.

        Higher score means a better tradeoff between timing and frame quality.
        This is intentionally heuristic and deterministic for local use.
        """
        quality_score = min(candidate.file_size / 10_000, 10.0)
        display_seconds = DraftGenerationWorker._timestamp_to_seconds(step.get("timestamp") or candidate.timestamp)
        start_seconds = DraftGenerationWorker._timestamp_to_seconds(
            step.get("start_timestamp") or step.get("timestamp") or candidate.timestamp
        )
        end_seconds = DraftGenerationWorker._timestamp_to_seconds(
            step.get("end_timestamp") or step.get("timestamp") or candidate.timestamp
        )
        candidate_seconds = DraftGenerationWorker._timestamp_to_seconds(candidate.timestamp)
        timing_penalty = abs(candidate_seconds - display_seconds)
        score = quality_score - timing_penalty

        if start_seconds <= candidate_seconds <= end_seconds:
            score += 3.0

        if action_type == "navigate" and candidate.offset_seconds >= 1:
            score += 2.5
        elif action_type == "data_entry" and 0 <= candidate.offset_seconds <= 2:
            score += 2.5
        elif action_type == "copy" and -2 <= candidate.offset_seconds <= 0:
            score += 2.0
        elif action_type == "submit" and candidate.offset_seconds >= 1:
            score += 2.5
        elif action_type == "default" and -1 <= candidate.offset_seconds <= 2:
            score += 1.5

        if candidate.file_size < 4_000:
            score -= 3.0
        return score

    @staticmethod
    def _timestamp_to_seconds(timestamp: str) -> int:
        """Convert HH:MM:SS into total seconds."""
        parts = [int(part) for part in (timestamp or "00:00:00").split(":")]
        while len(parts) < 3:
            parts.insert(0, 0)
        hours, minutes, seconds = parts[-3:]
        return (hours * 3600) + (minutes * 60) + seconds

    @staticmethod
    def _seconds_to_timestamp(total_seconds: int) -> str:
        """Convert total seconds into HH:MM:SS."""
        hours = total_seconds // 3600
        remainder = total_seconds % 3600
        minutes = remainder // 60
        seconds = remainder % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    @staticmethod
    def _mark_failed(db, session_id: str, detail: str | None = None) -> None:
        session = db.get(DraftSessionModel, session_id)
        if session is None:
            return
        session.status = "failed"
        failure_detail = (detail or "Background draft generation did not complete successfully.").strip()
        if len(failure_detail) > 500:
            failure_detail = f"{failure_detail[:497]}..."
        db.add(
            ActionLogModel(
                session_id=session_id,
                event_type="generation_failed",
                title="Draft generation failed",
                detail=failure_detail,
                actor="system",
            )
        )
        db.commit()

    def _record_stage(self, db, session_id: str, title: str, detail: str) -> None:
        self.action_log_service.record(
            db,
            session_id=session_id,
            event_type="generation_stage",
            title=title,
            detail=detail,
            actor="system",
        )
        db.commit()

    @staticmethod
    def _build_pairing_detail(transcript_artifacts: list[ArtifactModel], video_artifacts: list[ArtifactModel]) -> str:
        if not transcript_artifacts or not video_artifacts:
            return "No video/transcript pairing available."
        if len(video_artifacts) == 1 and len(transcript_artifacts) > 1:
            return "Using the first uploaded video for all transcripts because only one video is available."
        if len(video_artifacts) < len(transcript_artifacts):
            return (
                f"Pairing by upload order for the first {len(video_artifacts)} transcript/video set(s); "
                "remaining transcripts reuse the last uploaded video."
            )
        pair_count = min(len(transcript_artifacts), len(video_artifacts))
        return f"Pairing transcripts to videos by upload order for {pair_count} set(s)."
