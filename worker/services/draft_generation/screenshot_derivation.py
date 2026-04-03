from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from worker import bootstrap as _bootstrap  # noqa: F401
from app.core.observability import bind_log_context, get_logger

from app.models.artifact import ArtifactModel
from app.services.action_log_service import ActionLogService
from worker.bootstrap import get_backend_settings
from worker.services.draft_generation.stage_context import DraftGenerationContext
from worker.services.draft_generation.support import (
    SCREENSHOT_ROLE_LOCAL_OFFSETS,
    SCREENSHOT_ROLE_ORDER,
    build_pairing_detail,
    classify_action_type,
    seconds_to_timestamp,
    timestamp_to_seconds,
)
from worker.services.generation_types import DerivedScreenshotRecord, ScreenshotCandidateRecord, StepRecord
from worker.services.media.video_frame_extractor import ExtractedFrameCandidate, VideoFrameExtractor

logger = get_logger(__name__)


class _IsoformatValue(Protocol):
    def isoformat(self) -> str: ...


class ScreenshotDerivationStage:
    """Derive screenshot candidates and selected screenshots from video artifacts."""

    def __init__(self, *, frame_extractor: VideoFrameExtractor | None = None, action_log_service: ActionLogService | None = None) -> None:
        self.settings = get_backend_settings()
        self.frame_extractor = frame_extractor or VideoFrameExtractor(
            timeout_seconds=self.settings.screenshot_ffmpeg_timeout_seconds
        )
        self.action_log_service = action_log_service or ActionLogService()

    def run(self, db: Any, context: DraftGenerationContext) -> None:
        with bind_log_context(stage="screenshot_derivation"):
            if not context.video_artifacts:
                logger.info(
                    "Skipping screenshot derivation because no video artifacts are present",
                    extra={"event": "draft_generation.stage_skipped"},
                )
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

            active_transcripts = [
                transcript for transcript in self._sort_artifacts(context.transcript_artifacts) if context.steps_by_transcript.get(transcript.id)
            ]
            sorted_videos = self._sort_artifacts(context.video_artifacts)

            for transcript_index, transcript in enumerate(active_transcripts):
                transcript_steps = context.steps_by_transcript.get(transcript.id, [])
                if not transcript_steps:
                    continue
                paired_video = self._paired_video_for_transcript(
                    transcript=transcript,
                    active_transcripts=active_transcripts,
                    all_videos=sorted_videos,
                    fallback_transcript_index=transcript_index,
                )
                if paired_video is None:
                    continue
                logger.info(
                    "Starting screenshot extraction for transcript group",
                    extra={
                        "event": "draft_generation.screenshot_group_started",
                        "transcript_artifact_id": transcript.id,
                        "meeting_id": getattr(transcript, "meeting_id", None),
                        "video_artifact_id": paired_video.id,
                        "step_count": len(transcript_steps),
                    },
                )
                context.screenshot_artifacts.extend(
                    self._derive_screenshots(
                        db=db,
                        session_id=context.session_id,
                        video_artifacts=[paired_video],
                        step_candidates=transcript_steps,
                    )
                )
            logger.info(
                "Screenshot derivation completed",
                extra={
                    "event": "draft_generation.stage_completed",
                    "screenshot_count": len(context.screenshot_artifacts),
                },
            )

    @staticmethod
    def _sort_artifacts(artifacts: list[ArtifactModel]) -> list[ArtifactModel]:
        def _iso_or_empty(value: _IsoformatValue | None) -> str:
            return value.isoformat() if value is not None else ""

        return sorted(
            artifacts,
            key=lambda artifact: (
                getattr(getattr(artifact, "meeting", None), "order_index", None)
                if getattr(getattr(artifact, "meeting", None), "order_index", None) is not None
                else 1_000_000,
                _iso_or_empty(getattr(getattr(artifact, "meeting", None), "meeting_date", None)),
                _iso_or_empty(getattr(artifact, "created_at", None)),
                _iso_or_empty(getattr(getattr(artifact, "meeting", None), "uploaded_at", None)),
                artifact.id,
            ),
        )

    @staticmethod
    def _videos_for_transcript(*, transcript: ArtifactModel, all_videos: list[ArtifactModel]) -> list[ArtifactModel]:
        meeting_id = getattr(transcript, "meeting_id", None)
        if meeting_id:
            meeting_videos = [video for video in all_videos if getattr(video, "meeting_id", None) == meeting_id]
            if meeting_videos:
                return meeting_videos
        return all_videos

    def _paired_video_for_transcript(
        self,
        *,
        transcript: ArtifactModel,
        active_transcripts: list[ArtifactModel],
        all_videos: list[ArtifactModel],
        fallback_transcript_index: int,
    ) -> ArtifactModel | None:
        candidate_videos = self._videos_for_transcript(transcript=transcript, all_videos=all_videos)
        if not candidate_videos:
            return None

        transcript_batch_id = getattr(transcript, "upload_batch_id", None)
        transcript_pair_index = getattr(transcript, "upload_pair_index", None)
        if transcript_batch_id:
            batch_videos = [
                video
                for video in candidate_videos
                if getattr(video, "upload_batch_id", None) == transcript_batch_id
            ]
            if batch_videos:
                if transcript_pair_index is not None:
                    indexed_match = next(
                        (
                            video
                            for video in batch_videos
                            if getattr(video, "upload_pair_index", None) == transcript_pair_index
                        ),
                        None,
                    )
                    if indexed_match is not None:
                        return indexed_match
                return batch_videos[min(0, len(batch_videos) - 1)]

        meeting_id = getattr(transcript, "meeting_id", None)
        if meeting_id:
            meeting_transcripts = [item for item in active_transcripts if getattr(item, "meeting_id", None) == meeting_id]
            meeting_videos = [item for item in candidate_videos if getattr(item, "meeting_id", None) == meeting_id]
            if meeting_transcripts and meeting_videos:
                local_transcript_index = next(
                    (index for index, item in enumerate(meeting_transcripts) if item.id == transcript.id),
                    0,
                )
                return meeting_videos[min(local_transcript_index, len(meeting_videos) - 1)]

        return candidate_videos[min(fallback_transcript_index if len(candidate_videos) > 1 else 0, len(candidate_videos) - 1)]

    def _derive_screenshots(self, *, db, session_id: str, video_artifacts: list[ArtifactModel], step_candidates: list[StepRecord]) -> list[ArtifactModel]:
        if not video_artifacts or not self.frame_extractor.is_available():
            return []

        primary_video = video_artifacts[0]
        video_duration_seconds = self.frame_extractor.get_video_duration_seconds(video_path=primary_video.storage_path)
        screenshots: list[ArtifactModel] = []
        screenshots_dir = self.settings.local_storage_root / session_id / "generated-screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)

        total_steps = len(step_candidates)
        for step_index, step in enumerate(step_candidates, start=1):
            logger.info(
                "Extracting screenshot candidates for step",
                extra={
                    "event": "draft_generation.screenshot_step_started",
                    "video_artifact_id": primary_video.id,
                    "step_index": step_index,
                    "total_steps": total_steps,
                    "step_number": step.get("step_number"),
                    "meeting_id": step.get("meeting_id"),
                },
            )
            candidate_timestamps = self._build_candidate_timestamps(step, video_duration_seconds=video_duration_seconds)
            logger.info(
                "Prepared screenshot candidate timestamps",
                extra={
                    "event": "draft_generation.screenshot_timestamps_prepared",
                    "video_artifact_id": primary_video.id,
                    "step_index": step_index,
                    "total_steps": total_steps,
                    "step_number": step.get("step_number"),
                    "candidate_timestamps": candidate_timestamps,
                    "video_duration_seconds": video_duration_seconds,
                },
            )
            candidate_screenshots = self._derive_candidate_screenshot_pool(
                db=db,
                session_id=session_id,
                video_path=primary_video.storage_path,
                screenshots_dir=screenshots_dir,
                step=step,
                candidate_timestamps=candidate_timestamps,
            )
            if not candidate_screenshots:
                logger.info(
                    "No screenshot candidates derived for step",
                    extra={
                        "event": "draft_generation.screenshot_step_empty",
                        "video_artifact_id": primary_video.id,
                        "step_index": step_index,
                        "total_steps": total_steps,
                        "step_number": step.get("step_number"),
                    },
                )
                continue

            derived_screenshots = self._select_step_screenshot_slots(step=step, candidate_screenshots=candidate_screenshots)
            step["_candidate_screenshots"] = candidate_screenshots
            step["_derived_screenshots"] = derived_screenshots
            primary_screenshot = next((item for item in derived_screenshots if item["is_primary"]), derived_screenshots[0])
            step["screenshot_id"] = primary_screenshot["artifact"].id
            step["timestamp"] = primary_screenshot["timestamp"]
            screenshots.extend(item["artifact"] for item in candidate_screenshots)
            logger.info(
                "Completed screenshot candidates for step",
                extra={
                    "event": "draft_generation.screenshot_step_completed",
                    "video_artifact_id": primary_video.id,
                    "step_index": step_index,
                    "total_steps": total_steps,
                    "step_number": step.get("step_number"),
                    "candidate_count": len(candidate_screenshots),
                    "selected_count": len(derived_screenshots),
                },
            )
        db.commit()
        return screenshots

    def _window_sampling_is_reliable(self, step: StepRecord) -> bool:
        start_timestamp = str(step.get("start_timestamp") or "").strip()
        end_timestamp = str(step.get("end_timestamp") or "").strip()
        display_timestamp = str(step.get("timestamp") or "").strip()
        if not start_timestamp or not end_timestamp:
            return False

        start_seconds = timestamp_to_seconds(start_timestamp)
        end_seconds = timestamp_to_seconds(end_timestamp)
        if end_seconds < start_seconds:
            return False

        span_seconds = end_seconds - start_seconds
        if span_seconds <= 0 or span_seconds > self.settings.screenshot_window_max_seconds:
            return False

        if not step.get("evidence_references"):
            return False

        if display_timestamp:
            display_seconds = timestamp_to_seconds(display_timestamp)
            if not start_seconds <= display_seconds <= end_seconds:
                return False

        return True

    def _effective_span_seconds(
        self,
        step: StepRecord,
        *,
        video_duration_seconds: int | None,
    ) -> tuple[bool, int, int, int, int]:
        fallback_timestamp = step.get("timestamp") or "00:00:01"
        start_seconds = self._coerce_seconds_for_video(
            step.get("start_timestamp") or fallback_timestamp,
            video_duration_seconds=video_duration_seconds,
        )
        end_seconds = max(
            start_seconds,
            self._coerce_seconds_for_video(
                step.get("end_timestamp") or fallback_timestamp,
                video_duration_seconds=video_duration_seconds,
            ),
        )
        display_seconds = self._coerce_seconds_for_video(
            fallback_timestamp,
            video_duration_seconds=video_duration_seconds,
        )
        return (
            self._window_sampling_is_reliable(step),
            max(0, end_seconds - start_seconds),
            start_seconds,
            end_seconds,
            display_seconds,
        )

    def _ordered_unique_points(self, points: list[int]) -> list[int]:
        ordered: list[int] = []
        seen: set[int] = set()
        for point in points:
            normalized = max(1, point)
            if normalized in seen:
                continue
            seen.add(normalized)
            ordered.append(normalized)
        return ordered

    def _fill_points_to_limit(self, base_points: list[int], *, anchor_seconds: int, limit: int) -> list[int]:
        ordered = self._ordered_unique_points(base_points)
        if len(ordered) >= limit:
            return ordered[:limit]

        padding = max(1, self.settings.screenshot_anchor_padding_seconds)
        step_distance = 1
        while len(ordered) < limit:
            for direction in (-1, 1):
                candidate = anchor_seconds + (direction * padding * step_distance)
                candidate_points = self._ordered_unique_points(ordered + [candidate])
                if len(candidate_points) != len(ordered):
                    ordered = candidate_points
                if len(ordered) >= limit:
                    break
            step_distance += 1
        return ordered[:limit]

    @staticmethod
    def _split_timestamp_parts(value: str) -> tuple[int, int, int] | None:
        parts = str(value or "").split(":")
        if len(parts) != 3:
            return None
        try:
            return int(parts[0]), int(parts[1]), int(parts[2])
        except ValueError:
            return None

    def _coerce_seconds_for_video(self, timestamp_value: str, *, video_duration_seconds: int | None) -> int:
        parsed_seconds = timestamp_to_seconds(timestamp_value or "00:00:01")
        if not video_duration_seconds or parsed_seconds <= video_duration_seconds:
            return parsed_seconds

        parts = self._split_timestamp_parts(timestamp_value)
        if parts is not None:
            first, second, third = parts
            if third == 0:
                recovered_mmss_seconds = (first * 60) + second
                if 1 <= recovered_mmss_seconds <= video_duration_seconds:
                    logger.info(
                        "Recovered malformed step timestamp for screenshot extraction",
                        extra={
                            "event": "draft_generation.screenshot_timestamp_recovered",
                            "original_timestamp": timestamp_value,
                            "recovered_timestamp": seconds_to_timestamp(recovered_mmss_seconds),
                            "video_duration_seconds": video_duration_seconds,
                        },
                    )
                    return recovered_mmss_seconds

        logger.info(
            "Clamped out-of-range step timestamp for screenshot extraction",
            extra={
                "event": "draft_generation.screenshot_timestamp_clamped",
                "original_timestamp": timestamp_value,
                "clamped_timestamp": seconds_to_timestamp(video_duration_seconds),
                "video_duration_seconds": video_duration_seconds,
            },
        )
        return video_duration_seconds

    def _practical_candidate_limit(self, *, reliable_window: bool, span_seconds: int) -> int:
        configured_max = max(1, self.settings.screenshot_candidate_count)
        if not reliable_window:
            return min(configured_max, max(1, self.settings.screenshot_anchor_candidate_cap))
        if span_seconds <= self.settings.screenshot_short_window_seconds:
            return min(configured_max, max(1, self.settings.screenshot_short_window_candidate_cap))
        if span_seconds <= self.settings.screenshot_medium_window_seconds:
            return min(configured_max, max(1, self.settings.screenshot_medium_window_candidate_cap))
        if span_seconds <= self.settings.screenshot_long_window_seconds:
            return min(configured_max, max(1, self.settings.screenshot_long_window_candidate_cap))
        return min(configured_max, max(1, self.settings.screenshot_extended_window_candidate_cap))

    def _candidate_seconds_for_step(self, step: StepRecord, *, video_duration_seconds: int | None) -> list[int]:
        reliable_window, span_seconds, start_seconds, end_seconds, display_seconds = self._effective_span_seconds(
            step,
            video_duration_seconds=video_duration_seconds,
        )
        limit = self._practical_candidate_limit(reliable_window=reliable_window, span_seconds=span_seconds)

        if reliable_window:
            midpoint = start_seconds + ((end_seconds - start_seconds) // 2)
            return self._fill_points_to_limit(
                [start_seconds, midpoint, end_seconds],
                anchor_seconds=midpoint,
                limit=limit,
            )

        anchor_seconds = display_seconds or start_seconds or end_seconds
        return self._fill_points_to_limit([anchor_seconds], anchor_seconds=anchor_seconds, limit=limit)

    def _build_candidate_timestamps(self, step: StepRecord, *, video_duration_seconds: int | None) -> list[str]:
        return [
            seconds_to_timestamp(point)
            for point in self._candidate_seconds_for_step(step, video_duration_seconds=video_duration_seconds)
        ]

    def _derive_candidate_screenshot_pool(
        self,
        *,
        db,
        session_id: str,
        video_path: str,
        screenshots_dir: Path,
        step: StepRecord,
        candidate_timestamps: list[str],
    ) -> list[ScreenshotCandidateRecord]:
        extracted_candidates = self.frame_extractor.extract_frames_at_timestamps(
            video_path=video_path,
            output_dir=str(screenshots_dir),
            timestamps=candidate_timestamps,
            filename_prefix=f"step_{step['step_number']:03d}_candidate",
        )
        screenshot_candidates: list[ScreenshotCandidateRecord] = []
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

    def _select_step_screenshot_slots(self, *, step: StepRecord, candidate_screenshots: list[ScreenshotCandidateRecord]) -> list[DerivedScreenshotRecord]:
        if not candidate_screenshots:
            return []

        roles = self._select_screenshot_roles(step)
        roles = self._apply_selected_limit(roles)
        screenshots: list[DerivedScreenshotRecord] = []
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

    def _apply_selected_limit(self, roles: list[str]) -> list[str]:
        if not roles:
            return []

        max_selected = max(1, self.settings.screenshot_selected_count)
        if max_selected >= len(roles):
            return roles
        if max_selected == 1:
            return ["during"] if "during" in roles else [roles[-1]]
        if max_selected == 2:
            if "before" in roles and "after" in roles and "during" not in roles:
                return ["before", "after"]
            prioritized = [role for role in ("during", "after", "before") if role in roles]
            return prioritized[:2]
        prioritized = [role for role in ("before", "during", "after") if role in roles]
        return prioritized[:max_selected]

    def _select_best_candidate_record(self, step: StepRecord, candidates: list[ScreenshotCandidateRecord]) -> ScreenshotCandidateRecord | None:
        if not candidates:
            return None

        action_type = classify_action_type(step.get("action_text", ""))
        best_candidate: ScreenshotCandidateRecord | None = None
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

    def _select_screenshot_roles(self, step: StepRecord) -> list[str]:
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

    def _timestamp_for_role(self, step: StepRecord, role: str) -> str:
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
    def _score_candidate(action_type: str, candidate: ExtractedFrameCandidate, step: StepRecord) -> float:
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
