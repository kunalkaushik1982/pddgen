r"""
Purpose: Dedicated worker stages for draft generation.
Full filepath: C:\Users\work\Documents\PddGenerator\worker\services\draft_generation_stage_services.py
"""

import json
from pathlib import Path
from uuid import uuid4

from sqlalchemy import delete, select

from app.models.action_log import ActionLogModel
from app.models.artifact import ArtifactModel
from app.models.process_note import ProcessNoteModel
from app.models.process_step import ProcessStepModel
from app.models.process_step_screenshot import ProcessStepScreenshotModel
from app.models.process_step_screenshot_candidate import ProcessStepScreenshotCandidateModel
from app.services.action_log_service import ActionLogService
from app.services.step_extraction import StepExtractionService
from app.services.transcript_intelligence import TranscriptIntelligenceService
from worker.bootstrap import get_backend_settings
from worker.services.ai_transcript_interpreter import AITranscriptInterpreter
from worker.services.draft_generation_stage_context import DraftGenerationContext
from worker.services.draft_generation_support import (
    ACTION_OFFSET_WINDOWS,
    SCREENSHOT_ROLE_LOCAL_OFFSETS,
    SCREENSHOT_ROLE_ORDER,
    build_pairing_detail,
    classify_action_type,
    extract_transcript_timestamps,
    seconds_to_timestamp,
    timestamp_to_seconds,
)
from worker.services.transcript_normalizer import TranscriptNormalizer
from worker.services.video_frame_extractor import ExtractedFrameCandidate, VideoFrameExtractor


class SessionPreparationStage:
    """Load session inputs and clear stale generated entities."""

    def load_and_prepare(self, db, session) -> DraftGenerationContext:  # type: ignore[no-untyped-def]
        session.status = "processing"
        db.commit()

        transcript_artifacts = [artifact for artifact in session.artifacts if artifact.kind == "transcript"]
        video_artifacts = [artifact for artifact in session.artifacts if artifact.kind == "video"]
        if not transcript_artifacts:
            raise ValueError("No transcript artifacts found for draft generation.")

        step_ids_subquery = select(ProcessStepModel.id).where(ProcessStepModel.session_id == session.id)
        db.execute(delete(ProcessStepScreenshotModel).where(ProcessStepScreenshotModel.step_id.in_(step_ids_subquery)))
        db.execute(
            delete(ProcessStepScreenshotCandidateModel).where(
                ProcessStepScreenshotCandidateModel.step_id.in_(step_ids_subquery)
            )
        )
        db.execute(delete(ProcessStepModel).where(ProcessStepModel.session_id == session.id))
        db.execute(delete(ProcessNoteModel).where(ProcessNoteModel.session_id == session.id))
        db.execute(delete(ArtifactModel).where(ArtifactModel.session_id == session.id, ArtifactModel.kind == "screenshot"))
        db.commit()

        return DraftGenerationContext(
            session_id=session.id,
            session=session,
            transcript_artifacts=transcript_artifacts,
            video_artifacts=video_artifacts,
        )


class TranscriptInterpretationStage:
    """Interpret transcripts into normalized steps and notes."""

    def __init__(
        self,
        *,
        transcript_normalizer: TranscriptNormalizer | None = None,
        ai_transcript_interpreter: AITranscriptInterpreter | None = None,
        step_extractor: StepExtractionService | None = None,
        note_extractor: TranscriptIntelligenceService | None = None,
        action_log_service: ActionLogService | None = None,
    ) -> None:
        self.transcript_normalizer = transcript_normalizer or TranscriptNormalizer()
        self.ai_transcript_interpreter = ai_transcript_interpreter or AITranscriptInterpreter()
        self.step_extractor = step_extractor or StepExtractionService()
        self.note_extractor = note_extractor or TranscriptIntelligenceService()
        self.action_log_service = action_log_service or ActionLogService()

    def run(self, db, context: DraftGenerationContext) -> None:  # type: ignore[no-untyped-def]
        self.action_log_service.record(
            db,
            session_id=context.session_id,
            event_type="generation_stage",
            title="Interpreting transcript",
            detail=f"Processing {len(context.transcript_artifacts)} transcript artifact(s).",
            actor="system",
        )
        db.commit()

        for transcript in context.transcript_artifacts:
            normalized_text = self.transcript_normalizer.normalize(transcript.storage_path, transcript.name)
            interpretation = self.ai_transcript_interpreter.interpret(
                transcript_artifact_id=transcript.id,
                transcript_text=normalized_text,
            )

            if interpretation is not None and interpretation.steps:
                self._ground_ai_step_spans(interpretation.steps, normalized_text)
                context.all_steps.extend(interpretation.steps)
                context.steps_by_transcript.setdefault(transcript.id, []).extend(interpretation.steps)
                context.all_notes.extend(interpretation.notes)
                continue

            transcript_steps = self.step_extractor.extract_steps(
                transcript_artifact_id=transcript.id,
                transcript_text=normalized_text,
            )
            context.all_steps.extend(transcript_steps)
            context.steps_by_transcript.setdefault(transcript.id, []).extend(transcript_steps)
            context.all_notes.extend(
                self.note_extractor.extract_notes(
                    transcript_artifact_id=transcript.id,
                    transcript_text=normalized_text,
                )
            )

        for step_number, step in enumerate(context.all_steps, start=1):
            step["step_number"] = step_number

    def _ground_ai_step_spans(self, step_candidates: list[dict], transcript_text: str) -> None:
        transcript_timestamps = extract_transcript_timestamps(transcript_text)
        if not transcript_timestamps:
            return

        for index, step in enumerate(step_candidates):
            inferred_start = transcript_timestamps[index] if index < len(transcript_timestamps) else transcript_timestamps[-1]
            inferred_end = transcript_timestamps[index + 1] if (index + 1) < len(transcript_timestamps) else inferred_start

            if not str(step.get("start_timestamp", "") or ""):
                step["start_timestamp"] = inferred_start
            if not str(step.get("end_timestamp", "") or ""):
                step["end_timestamp"] = inferred_end
            if not str(step.get("timestamp", "") or ""):
                step["timestamp"] = step["start_timestamp"]
            if not str(step.get("supporting_transcript_text", "") or ""):
                step["supporting_transcript_text"] = step.get("action_text", "")

            if timestamp_to_seconds(step["end_timestamp"]) < timestamp_to_seconds(step["start_timestamp"]):
                step["end_timestamp"] = step["start_timestamp"]


class ScreenshotDerivationStage:
    """Derive screenshot candidates and selected screenshots from video artifacts."""

    def __init__(self, *, frame_extractor: VideoFrameExtractor | None = None, action_log_service: ActionLogService | None = None) -> None:
        self.settings = get_backend_settings()
        self.frame_extractor = frame_extractor or VideoFrameExtractor()
        self.action_log_service = action_log_service or ActionLogService()

    def run(self, db, context: DraftGenerationContext) -> None:  # type: ignore[no-untyped-def]
        if not context.video_artifacts:
            return

        self.action_log_service.record(
            db,
            session_id=context.session_id,
            event_type="generation_stage",
            title="Extracting screenshots",
            detail=build_pairing_detail(context.transcript_artifacts, context.video_artifacts),
            actor="system",
        )
        db.commit()

        for transcript_index, transcript in enumerate(context.transcript_artifacts):
            transcript_steps = context.steps_by_transcript.get(transcript.id, [])
            if not transcript_steps:
                continue
            paired_video = context.video_artifacts[min(transcript_index, len(context.video_artifacts) - 1)]
            context.screenshot_artifacts.extend(
                self._derive_screenshots(
                    db=db,
                    session_id=context.session_id,
                    video_artifacts=[paired_video],
                    step_candidates=transcript_steps,
                )
            )

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

            derived_screenshots = self._select_step_screenshot_slots(step=step, candidate_screenshots=candidate_screenshots)
            step["_candidate_screenshots"] = candidate_screenshots
            step["_derived_screenshots"] = derived_screenshots
            primary_screenshot = next((item for item in derived_screenshots if item["is_primary"]), derived_screenshots[0])
            step["screenshot_id"] = primary_screenshot["artifact"].id
            step["timestamp"] = primary_screenshot["timestamp"]
            screenshots.extend(item["artifact"] for item in candidate_screenshots)
        db.commit()
        return screenshots

    def _build_candidate_offsets(self, step: dict) -> list[int]:
        action_type = classify_action_type(step.get("action_text", ""))
        offsets = ACTION_OFFSET_WINDOWS.get(action_type, ACTION_OFFSET_WINDOWS["default"])
        if step.get("confidence") in {"low", "unknown"}:
            widened = offsets + [-4, 4, -5, 5]
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
        fallback_timestamp = step.get("timestamp") or "00:00:01"
        start_timestamp = step.get("start_timestamp") or fallback_timestamp
        end_timestamp = step.get("end_timestamp") or fallback_timestamp
        start_seconds = timestamp_to_seconds(start_timestamp)
        end_seconds = max(start_seconds, timestamp_to_seconds(end_timestamp))
        display_seconds = timestamp_to_seconds(fallback_timestamp)

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
        return [seconds_to_timestamp(point) for point in ordered_points]

    def _derive_candidate_screenshot_pool(
        self,
        *,
        db,
        session_id: str,
        video_path: str,
        screenshots_dir: Path,
        step: dict,
    ) -> list[dict]:
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
                scoped_candidates = [candidate for candidate in candidate_screenshots if candidate["artifact"].id not in used_artifact_ids]

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
        if not candidates:
            return None

        action_type = classify_action_type(step.get("action_text", ""))
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
        span_seconds = max(
            0,
            timestamp_to_seconds(step.get("end_timestamp") or step.get("timestamp") or "00:00:01")
            - timestamp_to_seconds(step.get("start_timestamp") or step.get("timestamp") or "00:00:01"),
        )
        action_type = classify_action_type(step.get("action_text", ""))
        if span_seconds <= 2:
            return ["during"]
        if span_seconds <= 6:
            if action_type in {"navigate", "submit"}:
                return ["before", "after"]
            return ["during", "after"]
        return list(SCREENSHOT_ROLE_ORDER)

    def _timestamp_for_role(self, step: dict, role: str) -> str:
        start_seconds = timestamp_to_seconds(step.get("start_timestamp") or step.get("timestamp") or "00:00:01")
        end_seconds = max(start_seconds, timestamp_to_seconds(step.get("end_timestamp") or step.get("timestamp") or "00:00:01"))
        if role == "before":
            return seconds_to_timestamp(start_seconds)
        if role == "after":
            return seconds_to_timestamp(end_seconds)
        midpoint = start_seconds + ((end_seconds - start_seconds) // 2)
        return seconds_to_timestamp(midpoint)

    def _candidate_timestamps_for_role(self, base_timestamp: str, role: str) -> list[str]:
        base_seconds = timestamp_to_seconds(base_timestamp)
        offsets = SCREENSHOT_ROLE_LOCAL_OFFSETS.get(role, [0])
        points = [max(1, base_seconds + offset) for offset in offsets]
        ordered: list[int] = []
        seen: set[int] = set()
        for point in points:
            if point in seen:
                continue
            seen.add(point)
            ordered.append(point)
        return [seconds_to_timestamp(point) for point in ordered]

    @staticmethod
    def _score_candidate(action_type: str, candidate: ExtractedFrameCandidate, step: dict) -> float:
        quality_score = min(candidate.file_size / 10_000, 10.0)
        display_seconds = timestamp_to_seconds(step.get("timestamp") or candidate.timestamp)
        start_seconds = timestamp_to_seconds(step.get("start_timestamp") or step.get("timestamp") or candidate.timestamp)
        end_seconds = timestamp_to_seconds(step.get("end_timestamp") or step.get("timestamp") or candidate.timestamp)
        candidate_seconds = timestamp_to_seconds(candidate.timestamp)
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


class DiagramAssemblyStage:
    """Build diagram JSON payloads for the generated draft."""

    def __init__(self, *, ai_transcript_interpreter: AITranscriptInterpreter | None = None, action_log_service: ActionLogService | None = None) -> None:
        self.ai_transcript_interpreter = ai_transcript_interpreter or AITranscriptInterpreter()
        self.action_log_service = action_log_service or ActionLogService()

    def run(self, db, context: DraftGenerationContext) -> None:  # type: ignore[no-untyped-def]
        self.action_log_service.record(
            db,
            session_id=context.session_id,
            event_type="generation_stage",
            title="Building diagram",
            detail="Generating the session diagram model.",
            actor="system",
        )
        db.commit()

        diagram_interpretation = None
        try:
            diagram_interpretation = self.ai_transcript_interpreter.interpret_diagrams(
                session_title=context.session.title,
                diagram_type=context.session.diagram_type,
                steps=context.all_steps,
                notes=context.all_notes,
            )
        except Exception:
            diagram_interpretation = None

        if diagram_interpretation is None:
            context.overview_diagram_json = ""
            context.detailed_diagram_json = ""
            return

        context.overview_diagram_json = json.dumps(diagram_interpretation.overview)
        context.detailed_diagram_json = json.dumps(diagram_interpretation.detailed)


class PersistenceStage:
    """Persist generated steps, notes, screenshots, and final status."""

    def run(self, db, context: DraftGenerationContext) -> dict[str, int | str]:  # type: ignore[no-untyped-def]
        context.session.overview_diagram_json = context.overview_diagram_json
        context.session.detailed_diagram_json = context.detailed_diagram_json

        step_models = [ProcessStepModel(session_id=context.session_id, **self._to_step_record(step)) for step in context.all_steps]
        db.add_all(step_models)
        db.flush()
        self._persist_step_screenshots(db, step_models, context.all_steps)
        db.add_all(ProcessNoteModel(session_id=context.session_id, **note) for note in context.all_notes)
        context.session.status = "review"
        db.add(
            ActionLogModel(
                session_id=context.session_id,
                event_type="draft_generated",
                title="Ready for review",
                detail=(
                    f"{len(context.all_steps)} steps, "
                    f"{len(context.all_notes)} notes, "
                    f"{len(context.screenshot_artifacts)} screenshots."
                ),
                actor="system",
            )
        )
        db.commit()
        return {
            "session_id": context.session_id,
            "steps_created": len(context.all_steps),
            "notes_created": len(context.all_notes),
            "screenshots_created": len(context.screenshot_artifacts),
        }

    @staticmethod
    def _attach_screenshot_evidence(step: dict) -> None:
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

    def _persist_step_screenshots(self, db, step_models: list[ProcessStepModel], step_candidates: list[dict]) -> None:  # type: ignore[no-untyped-def]
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
        return {key: value for key, value in step.items() if key not in {"_candidate_screenshots", "_derived_screenshots"}}


class FailureStage:
    """Persist failure state for background generation errors."""

    @staticmethod
    def mark_failed(db, session_id: str, detail: str | None = None) -> None:  # type: ignore[no-untyped-def]
        from app.models.draft_session import DraftSessionModel

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
