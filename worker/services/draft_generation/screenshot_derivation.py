from __future__ import annotations

from pathlib import Path
from typing import Protocol

from worker import bootstrap as _bootstrap  # noqa: F401
from app.core.observability import bind_log_context, get_logger
from app.models.artifact import ArtifactModel
from app.services.action_log_service import ActionLogService
from worker.bootstrap import get_backend_settings
from worker.services.draft_generation.stage_context import DraftGenerationContext
from worker.services.generation_types import DerivedScreenshotRecord, ScreenshotCandidateRecord, StepRecord
from worker.services.draft_generation.screenshot_selection import (
    apply_selected_limit,
    candidate_timestamps_for_role,
    score_candidate,
    select_best_candidate_record,
    select_screenshot_roles,
    select_step_screenshot_slots,
    timestamp_for_role,
)
from worker.services.draft_generation.screenshot_timing import (
    build_candidate_timestamps,
    candidate_seconds_for_step,
    coerce_seconds_for_video,
    effective_span_seconds,
    fill_points_to_limit,
    ordered_unique_points,
    practical_candidate_limit,
    split_timestamp_parts,
    window_sampling_is_reliable,
)
from worker.services.draft_generation.support import (
    SCREENSHOT_ROLE_LOCAL_OFFSETS,
    SCREENSHOT_ROLE_ORDER,
    build_pairing_detail,
    classify_action_type,
    seconds_to_timestamp,
    timestamp_to_seconds,
)
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

    def run(self, db, context: DraftGenerationContext) -> None:  # type: ignore[no-untyped-def]
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
        return window_sampling_is_reliable(step, max_window_seconds=self.settings.screenshot_window_max_seconds)

    def _effective_span_seconds(
        self,
        step: StepRecord,
        *,
        video_duration_seconds: int | None,
    ) -> tuple[bool, int, int, int, int]:
        return effective_span_seconds(
            step,
            video_duration_seconds=video_duration_seconds,
            max_window_seconds=self.settings.screenshot_window_max_seconds,
        )

    def _ordered_unique_points(self, points: list[int]) -> list[int]:
        return ordered_unique_points(points)

    def _fill_points_to_limit(self, base_points: list[int], *, anchor_seconds: int, limit: int) -> list[int]:
        return fill_points_to_limit(
            base_points,
            anchor_seconds=anchor_seconds,
            limit=limit,
            anchor_padding_seconds=self.settings.screenshot_anchor_padding_seconds,
        )

    @staticmethod
    def _split_timestamp_parts(value: str) -> tuple[int, int, int] | None:
        return split_timestamp_parts(value)

    def _coerce_seconds_for_video(self, timestamp_value: str, *, video_duration_seconds: int | None) -> int:
        return coerce_seconds_for_video(timestamp_value, video_duration_seconds=video_duration_seconds)

    def _practical_candidate_limit(self, *, reliable_window: bool, span_seconds: int) -> int:
        return practical_candidate_limit(
            reliable_window=reliable_window,
            span_seconds=span_seconds,
            candidate_count=self.settings.screenshot_candidate_count,
            anchor_candidate_cap=self.settings.screenshot_anchor_candidate_cap,
            short_window_seconds=self.settings.screenshot_short_window_seconds,
            short_window_candidate_cap=self.settings.screenshot_short_window_candidate_cap,
            medium_window_seconds=self.settings.screenshot_medium_window_seconds,
            medium_window_candidate_cap=self.settings.screenshot_medium_window_candidate_cap,
            long_window_seconds=self.settings.screenshot_long_window_seconds,
            long_window_candidate_cap=self.settings.screenshot_long_window_candidate_cap,
            extended_window_candidate_cap=self.settings.screenshot_extended_window_candidate_cap,
        )

    def _candidate_seconds_for_step(self, step: StepRecord, *, video_duration_seconds: int | None) -> list[int]:
        return candidate_seconds_for_step(step, video_duration_seconds=video_duration_seconds, settings=self.settings)

    def _build_candidate_timestamps(self, step: StepRecord, *, video_duration_seconds: int | None) -> list[str]:
        return build_candidate_timestamps(step, video_duration_seconds=video_duration_seconds, settings=self.settings)

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
        return select_step_screenshot_slots(
            step=step,
            candidate_screenshots=candidate_screenshots,
            selected_count=self.settings.screenshot_selected_count,
        )

    def _apply_selected_limit(self, roles: list[str]) -> list[str]:
        return apply_selected_limit(roles, selected_count=self.settings.screenshot_selected_count)

    def _select_best_candidate_record(self, step: StepRecord, candidates: list[ScreenshotCandidateRecord]) -> ScreenshotCandidateRecord | None:
        return select_best_candidate_record(step, candidates)

    def _select_screenshot_roles(self, step: StepRecord) -> list[str]:
        return select_screenshot_roles(step)

    def _timestamp_for_role(self, step: StepRecord, role: str) -> str:
        return timestamp_for_role(step, role)

    def _candidate_timestamps_for_role(self, base_timestamp: str, role: str) -> list[str]:
        return candidate_timestamps_for_role(base_timestamp, role)

    @staticmethod
    def _score_candidate(action_type: str, candidate: ExtractedFrameCandidate, step: StepRecord) -> float:
        return score_candidate(action_type, candidate, step)
