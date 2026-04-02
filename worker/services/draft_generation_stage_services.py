r"""
Purpose: Dedicated worker stages for draft generation.
Full filepath: C:\Users\work\Documents\PddGenerator\worker\services\draft_generation_stage_services.py
"""

import json
from collections import Counter
from pathlib import Path
from typing import Protocol, TypedDict
from uuid import uuid4

from worker import bootstrap as _bootstrap  # noqa: F401
from app.core.observability import bind_log_context, get_logger
from sqlalchemy import delete, select

from app.models.action_log import ActionLogModel
from app.models.artifact import ArtifactModel
from app.models.meeting_evidence_bundle import MeetingEvidenceBundleModel
from app.models.process_note import ProcessNoteModel
from app.models.process_group import ProcessGroupModel
from app.models.process_step import ProcessStepModel
from app.models.process_step_screenshot import ProcessStepScreenshotModel
from app.models.process_step_screenshot_candidate import ProcessStepScreenshotCandidateModel
from app.services.action_log_service import ActionLogService
from app.services.step_extraction import StepExtractionService
from app.services.transcript_intelligence import TranscriptIntelligenceService
from worker.bootstrap import get_backend_settings
from worker.services.ai_skills.diagram_generation.schemas import DiagramGenerationRequest
from worker.services.ai_skills.registry import build_default_ai_skill_registry
from worker.services.canonical_process_merge import CanonicalProcessMergeService
from worker.services.ai_transcript_interpreter import AITranscriptInterpreter
from worker.services.draft_generation_stage_context import DraftGenerationContext
from worker.services.evidence_segmentation_service import (
    AISemanticEnrichmentStrategy,
    AIWorkflowBoundaryStrategy,
    EvidenceSegmentationService,
    HeuristicSemanticEnrichmentStrategy,
    ParagraphTranscriptSegmentationStrategy,
)
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
from worker.services.process_grouping_service import ProcessGroupingService
from worker.services.transcript_normalizer import TranscriptNormalizer
from worker.services.video_frame_extractor import ExtractedFrameCandidate, VideoFrameExtractor
from worker.services.workflow_strategy_registry import WorkflowIntelligenceStrategyRegistry

logger = get_logger(__name__)


class _TranscriptSummaryBuckets(TypedDict):
    transcript_name: str
    top_actors: Counter[str]
    top_objects: Counter[str]
    top_systems: Counter[str]
    top_goals: Counter[str]
    top_rules: Counter[str]


class _IsoformatValue(Protocol):
    def isoformat(self) -> str: ...


class SessionPreparationStage:
    """Load session inputs and clear stale generated entities."""

    def load_and_prepare(self, db, session) -> DraftGenerationContext:  # type: ignore[no-untyped-def]
        with bind_log_context(stage="session_preparation"):
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
            db.execute(delete(ProcessGroupModel).where(ProcessGroupModel.session_id == session.id))
            db.execute(delete(ArtifactModel).where(ArtifactModel.session_id == session.id, ArtifactModel.kind == "screenshot"))
            db.commit()
            logger.info(
                "Prepared session for generation",
                extra={
                    "event": "draft_generation.stage_completed",
                    "transcript_artifact_count": len(transcript_artifacts),
                    "video_artifact_count": len(video_artifacts),
                },
            )

            return DraftGenerationContext(
                session_id=session.id,
                session=session,
                document_type=getattr(session, "document_type", "pdd"),
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
        with bind_log_context(stage="transcript_interpretation"):
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
                normalized_text = context.normalized_transcripts.get(transcript.id)
                if normalized_text is None:
                    normalized_text = self.transcript_normalizer.normalize(transcript.storage_path, transcript.name)
                    context.normalized_transcripts[transcript.id] = normalized_text
                interpretation = self.ai_transcript_interpreter.interpret(
                    transcript_artifact_id=transcript.id,
                    transcript_text=normalized_text,
                )

                if interpretation is not None and interpretation.steps:
                    self._ground_ai_step_spans(interpretation.steps, normalized_text)
                    for step in interpretation.steps:
                        step["_transcript_artifact_id"] = transcript.id
                        step["process_group_id"] = context.default_process_group_id
                        step["meeting_id"] = getattr(transcript, "meeting_id", None)
                    context.all_steps.extend(interpretation.steps)
                    context.steps_by_transcript.setdefault(transcript.id, []).extend(interpretation.steps)
                    for note in interpretation.notes:
                        note["_transcript_artifact_id"] = transcript.id
                        note["process_group_id"] = context.default_process_group_id
                        note["meeting_id"] = getattr(transcript, "meeting_id", None)
                    context.all_notes.extend(interpretation.notes)
                    context.notes_by_transcript.setdefault(transcript.id, []).extend(interpretation.notes)
                    continue

                transcript_steps = self.step_extractor.extract_steps(
                    transcript_artifact_id=transcript.id,
                    transcript_text=normalized_text,
                )
                for step in transcript_steps:
                    step["_transcript_artifact_id"] = transcript.id
                    step["process_group_id"] = context.default_process_group_id
                    step["meeting_id"] = getattr(transcript, "meeting_id", None)
                context.all_steps.extend(transcript_steps)
                context.steps_by_transcript.setdefault(transcript.id, []).extend(transcript_steps)
                transcript_notes = self.note_extractor.extract_notes(
                    transcript_artifact_id=transcript.id,
                    transcript_text=normalized_text,
                )
                for note in transcript_notes:
                    note["_transcript_artifact_id"] = transcript.id
                    note["process_group_id"] = context.default_process_group_id
                    note["meeting_id"] = getattr(transcript, "meeting_id", None)
                context.all_notes.extend(transcript_notes)
                context.notes_by_transcript.setdefault(transcript.id, []).extend(transcript_notes)

            logger.info(
                "Transcript interpretation completed",
                extra={
                    "event": "draft_generation.stage_completed",
                    "step_count": len(context.all_steps),
                    "note_count": len(context.all_notes),
                },
            )

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


class EvidenceSegmentationStage:
    """Build non-persistent evidence segments and first-pass boundary decisions."""

    def __init__(
        self,
        *,
        transcript_normalizer: TranscriptNormalizer | None = None,
        segmentation_service: EvidenceSegmentationService,
        action_log_service: ActionLogService | None = None,
    ) -> None:
        self.transcript_normalizer = transcript_normalizer or TranscriptNormalizer()
        self.segmentation_service = segmentation_service
        self.action_log_service = action_log_service or ActionLogService()

    def run(self, db, context: DraftGenerationContext) -> None:  # type: ignore[no-untyped-def]
        with bind_log_context(stage="evidence_segmentation"):
            action_log = self.action_log_service.record(
                db,
                session_id=context.session_id,
                event_type="generation_stage",
                title="Segmenting evidence",
                detail=f"Building evidence segments for {len(context.transcript_artifacts)} transcript artifact(s).",
                actor="system",
            )
            db.commit()

            all_segments = []
            for transcript in context.transcript_artifacts:
                normalized_text = self.transcript_normalizer.normalize(transcript.storage_path, transcript.name)
                context.normalized_transcripts[transcript.id] = normalized_text
                all_segments.extend(
                    self.segmentation_service.segment_transcript(
                        transcript_artifact_id=transcript.id,
                        meeting_id=getattr(transcript, "meeting_id", None),
                        transcript_text=normalized_text,
                    )
                )

            context.evidence_segments = all_segments
            context.workflow_boundary_decisions = self.segmentation_service.infer_boundary_decisions(all_segments)
            action_log.metadata_json = json.dumps(self._build_segmentation_metadata(context))
            logger.info(
                "Evidence segmentation completed",
                extra={
                    "event": "draft_generation.stage_completed",
                    "segment_count": len(context.evidence_segments),
                    "boundary_decision_count": len(context.workflow_boundary_decisions),
                    "segmentation_strategy": self.segmentation_service.segmenter.strategy_key,
                    "enrichment_strategy": self.segmentation_service.enricher.strategy_key,
                    "boundary_strategy": self.segmentation_service.boundary_detector.strategy_key,
                },
            )

    def _build_segmentation_metadata(self, context: DraftGenerationContext) -> dict:
        segment_method_counts = Counter(segment.segmentation_method for segment in context.evidence_segments)
        enrichment_confidence_counts = Counter(
            segment.enrichment.confidence for segment in context.evidence_segments if segment.enrichment is not None
        )
        enrichment_source_counts = Counter(
            segment.enrichment.enrichment_source for segment in context.evidence_segments if segment.enrichment is not None
        )
        boundary_decision_counts = Counter(decision.decision for decision in context.workflow_boundary_decisions)
        boundary_confidence_counts = Counter(decision.confidence for decision in context.workflow_boundary_decisions)
        boundary_source_counts = Counter(decision.decision_source for decision in context.workflow_boundary_decisions)
        boundary_conflict_counts = Counter(
            "conflict" if decision.conflict_detected else "non_conflict"
            for decision in context.workflow_boundary_decisions
        )
        transcript_summaries: dict[str, _TranscriptSummaryBuckets] = {}
        transcript_names = {artifact.id: artifact.name for artifact in context.transcript_artifacts}
        for segment in context.evidence_segments:
            summary = transcript_summaries.setdefault(
                segment.transcript_artifact_id,
                _TranscriptSummaryBuckets(
                    transcript_name=transcript_names.get(segment.transcript_artifact_id, segment.transcript_artifact_id),
                    top_actors=Counter(),
                    top_objects=Counter(),
                    top_systems=Counter(),
                    top_goals=Counter(),
                    top_rules=Counter(),
                ),
            )
            if segment.enrichment is None:
                continue
            if segment.enrichment.actor:
                summary["top_actors"][segment.enrichment.actor] += 1
            if segment.enrichment.business_object:
                summary["top_objects"][segment.enrichment.business_object] += 1
            if segment.enrichment.system_name:
                summary["top_systems"][segment.enrichment.system_name] += 1
            if segment.enrichment.workflow_goal:
                summary["top_goals"][segment.enrichment.workflow_goal] += 1
            for rule_hint in segment.enrichment.rule_hints:
                summary["top_rules"][rule_hint] += 1
        sample_segments = []
        for segment in context.evidence_segments[:5]:
            sample_segments.append(
                {
                    "segment_id": segment.id,
                    "transcript_artifact_id": segment.transcript_artifact_id,
                    "segment_order": segment.segment_order,
                    "start_timestamp": segment.start_timestamp,
                    "end_timestamp": segment.end_timestamp,
                    "segmentation_method": segment.segmentation_method,
                    "confidence": segment.confidence,
                    "actor": segment.enrichment.actor if segment.enrichment is not None else None,
                    "actor_role": segment.enrichment.actor_role if segment.enrichment is not None else None,
                    "system_name": segment.enrichment.system_name if segment.enrichment is not None else None,
                    "action_verb": segment.enrichment.action_verb if segment.enrichment is not None else None,
                    "action_type": segment.enrichment.action_type if segment.enrichment is not None else None,
                    "business_object": segment.enrichment.business_object if segment.enrichment is not None else None,
                    "workflow_goal": segment.enrichment.workflow_goal if segment.enrichment is not None else None,
                    "rule_hints": segment.enrichment.rule_hints if segment.enrichment is not None else [],
                    "enrichment_source": segment.enrichment.enrichment_source if segment.enrichment is not None else "unknown",
                }
            )
        return {
            "conclusion": (
                f"Built {len(context.evidence_segments)} evidence segment(s) across {len(context.transcript_artifacts)} transcript(s). "
                f"Boundary classifier produced {len(context.workflow_boundary_decisions)} adjacent decision(s)."
            ),
            "document_type": context.document_type,
            "strategy_keys": {
                "segmenter": self.segmentation_service.segmenter.strategy_key,
                "enricher": self.segmentation_service.enricher.strategy_key,
                "boundary_detector": self.segmentation_service.boundary_detector.strategy_key,
            },
            "counts": {
                "transcript_artifacts": len(context.transcript_artifacts),
                "segments": len(context.evidence_segments),
                "boundary_decisions": len(context.workflow_boundary_decisions),
            },
            "segment_methods": dict(segment_method_counts),
            "enrichment_confidence": dict(enrichment_confidence_counts),
            "enrichment_sources": dict(enrichment_source_counts),
            "boundary_decisions": dict(boundary_decision_counts),
            "boundary_confidence": dict(boundary_confidence_counts),
            "decision_sources": dict(boundary_source_counts),
            "boundary_conflicts": dict(boundary_conflict_counts),
            "transcript_summaries": [
                {
                    "transcript_name": summary["transcript_name"],
                    "top_actors": [value for value, _ in summary["top_actors"].most_common(2)],
                    "top_objects": [value for value, _ in summary["top_objects"].most_common(2)],
                    "top_systems": [value for value, _ in summary["top_systems"].most_common(2)],
                    "top_goals": [value for value, _ in summary["top_goals"].most_common(2)],
                    "top_rules": [value for value, _ in summary["top_rules"].most_common(2)],
                }
                for summary in transcript_summaries.values()
            ],
            "sample_segments": sample_segments,
        }


class CanonicalMergeStage:
    """Merge meeting-specific outputs into one current canonical process."""

    def __init__(
        self,
        *,
        merge_service: CanonicalProcessMergeService | None = None,
        action_log_service: ActionLogService | None = None,
    ) -> None:
        self.merge_service = merge_service or CanonicalProcessMergeService()
        self.action_log_service = action_log_service or ActionLogService()

    def run(self, db, context: DraftGenerationContext) -> None:  # type: ignore[no-untyped-def]
        with bind_log_context(stage="canonical_merge"):
            self.action_log_service.record(
                db,
                session_id=context.session_id,
                event_type="generation_stage",
                title="Merging meeting evidence",
                detail=f"Canonicalizing process evidence from {len(context.transcript_artifacts)} transcript artifact(s).",
                actor="system",
            )
            db.commit()

            merge_result = self.merge_service.merge(
                transcript_artifacts=context.transcript_artifacts,
                process_groups=context.process_groups,
                steps_by_transcript=context.steps_by_transcript,
                notes_by_transcript=context.notes_by_transcript,
            )
            context.all_steps = merge_result.steps
            context.all_notes = merge_result.notes
            context.steps_by_transcript = merge_result.steps_by_transcript
            context.notes_by_transcript = merge_result.notes_by_transcript

            logger.info(
                "Canonical merge completed",
                extra={
                    "event": "draft_generation.stage_completed",
                    "canonical_step_count": len(context.all_steps),
                    "canonical_note_count": len(context.all_notes),
                },
            )


class ProcessGroupingStage:
    """Assign transcript outputs into logical process groups before canonical merge."""

    def __init__(
        self,
        *,
        grouping_service: ProcessGroupingService | None = None,
        action_log_service: ActionLogService | None = None,
    ) -> None:
        self.grouping_service = grouping_service or ProcessGroupingService()
        self.action_log_service = action_log_service or ActionLogService()

    def run(self, db, context: DraftGenerationContext) -> None:  # type: ignore[no-untyped-def]
        with bind_log_context(stage="process_grouping"):
            action_log = self.action_log_service.record(
                db,
                session_id=context.session_id,
                event_type="generation_stage",
                title="Grouping processes",
                detail=f"Clustering transcript evidence into logical process groups for {len(context.transcript_artifacts)} transcript artifact(s).",
                actor="system",
            )
            db.commit()

            grouping_result = self.grouping_service.assign_groups(
                db=db,
                session=context.session,
                transcript_artifacts=context.transcript_artifacts,
                steps_by_transcript=context.steps_by_transcript,
                notes_by_transcript=context.notes_by_transcript,
                evidence_segments=context.evidence_segments,
                workflow_boundary_decisions=context.workflow_boundary_decisions,
            )
            context.process_groups = grouping_result.process_groups
            ambiguous_assignments = [
                assignment
                for assignment in grouping_result.assignment_details
                if bool(assignment.get("is_ambiguous"))
            ]
            grouping_decision_sources = Counter(
                str(assignment.get("decision_source", "unknown") or "unknown")
                for assignment in grouping_result.assignment_details
            )
            grouping_conflicts = Counter(
                "conflict" if bool(assignment.get("conflict_detected")) else "non_conflict"
                for assignment in grouping_result.assignment_details
            )
            action_log.metadata_json = json.dumps(
                {
                    "conclusion": (
                        f"Created {len(grouping_result.process_groups)} process group(s) from "
                        f"{len(context.transcript_artifacts)} transcript artifact(s). "
                        f"{len(ambiguous_assignments)} assignment(s) were marked ambiguous for later review."
                    ),
                    "document_type": context.document_type,
                    "counts": {
                        "transcript_artifacts": len(context.transcript_artifacts),
                        "segmented_transcripts": len({segment.transcript_artifact_id for segment in context.evidence_segments}),
                        "process_groups": len(grouping_result.process_groups),
                        "ambiguous_assignments": len(ambiguous_assignments),
                    },
                    "transcript_assignments": grouping_result.transcript_group_ids,
                    "ambiguity_summary": {
                        "ambiguous_assignment_count": len(ambiguous_assignments),
                        "has_ambiguity": bool(ambiguous_assignments),
                    },
                    "decision_sources": dict(grouping_decision_sources),
                    "grouping_conflicts": dict(grouping_conflicts),
                    "process_group_summaries": [
                        {
                            "title": group.title,
                            "capability_tags": json.loads(getattr(group, "capability_tags_json", "[]") or "[]"),
                            "summary_text": getattr(group, "summary_text", "") or "",
                        }
                        for group in grouping_result.process_groups
                    ],
                    "assignments": grouping_result.assignment_details,
                }
            )
            logger.info(
                "Process grouping completed",
                extra={
                    "event": "draft_generation.stage_completed",
                    "process_group_count": len(grouping_result.process_groups),
                    "segmented_transcript_count": len({segment.transcript_artifact_id for segment in context.evidence_segments}),
                },
            )


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

    def _derive_screenshots(self, *, db, session_id: str, video_artifacts: list[ArtifactModel], step_candidates: list[dict]) -> list[ArtifactModel]:
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

    def _window_sampling_is_reliable(self, step: dict) -> bool:
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
        step: dict,
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

    def _candidate_seconds_for_step(self, step: dict, *, video_duration_seconds: int | None) -> list[int]:
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

    def _build_candidate_timestamps(self, step: dict, *, video_duration_seconds: int | None) -> list[str]:
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
        step: dict,
        candidate_timestamps: list[str],
    ) -> list[dict]:
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
        roles = self._apply_selected_limit(roles)
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
        self._ai_skill_registry = build_default_ai_skill_registry()
        self._diagram_generation_skill = None

    def run(self, db, context: DraftGenerationContext) -> None:  # type: ignore[no-untyped-def]
        with bind_log_context(stage="diagram_assembly"):
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
                if self._diagram_generation_skill is None:
                    self._diagram_generation_skill = self._ai_skill_registry.create("diagram_generation")
                logger.info(
                    "Delegating diagram generation to AI skill.",
                    extra={
                        "skill_id": "diagram_generation",
                        "skill_version": getattr(self._diagram_generation_skill, "version", "unknown"),
                        "session_title": context.session.title,
                    },
                )
                diagram_interpretation = self._diagram_generation_skill.run(
                    DiagramGenerationRequest(
                        session_title=context.session.title,
                        diagram_type=context.session.diagram_type,
                        steps=context.all_steps,
                        notes=context.all_notes,
                    )
                )
            except Exception:
                diagram_interpretation = None

            if diagram_interpretation is None:
                context.overview_diagram_json = ""
                context.detailed_diagram_json = ""
                logger.info("Diagram assembly produced no renderable output", extra={"event": "draft_generation.stage_completed"})
                return

            context.overview_diagram_json = json.dumps(diagram_interpretation.overview)
            context.detailed_diagram_json = json.dumps(diagram_interpretation.detailed)
            logger.info("Diagram assembly completed", extra={"event": "draft_generation.stage_completed"})


class PersistenceStage:
    """Persist generated steps, notes, screenshots, and final status."""

    def run(self, db, context: DraftGenerationContext) -> dict[str, int | str]:  # type: ignore[no-untyped-def]
        with bind_log_context(stage="persistence"):
            selected_screenshot_count = sum(len(step.get("_derived_screenshots", [])) for step in context.all_steps)
            context.session.overview_diagram_json = context.overview_diagram_json
            context.session.detailed_diagram_json = context.detailed_diagram_json

            step_models = [ProcessStepModel(session_id=context.session_id, **self._to_step_record(step)) for step in context.all_steps]
            db.add_all(step_models)
            db.flush()
            self._persist_step_screenshots(db, step_models, context.all_steps)
            db.add_all(ProcessNoteModel(session_id=context.session_id, **self._to_note_record(note)) for note in context.all_notes)
            pending_bundles = (
                db.execute(
                    select(MeetingEvidenceBundleModel).where(
                        MeetingEvidenceBundleModel.session_id == context.session_id,
                        MeetingEvidenceBundleModel.status == "pending",
                    )
                )
                .scalars()
                .all()
            )
            for bundle in pending_bundles:
                bundle.status = "processed"
            context.session.status = "review"
            db.add(
                ActionLogModel(
                    session_id=context.session_id,
                    event_type="draft_generated",
                    title="Ready for review",
                    detail=(
                        f"{len(context.all_steps)} steps, "
                        f"{len(context.all_notes)} notes, "
                        f"{selected_screenshot_count} screenshots."
                    ),
                    actor="system",
                )
            )
            db.commit()
            result = {
                "session_id": context.session_id,
                "steps_created": len(context.all_steps),
                "notes_created": len(context.all_notes),
                "screenshots_created": selected_screenshot_count,
            }
            logger.info("Persistence stage completed", extra={"event": "draft_generation.stage_completed", **result})
            return result

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
        record = {
            key: value
            for key, value in step.items()
            if key not in {"_candidate_screenshots", "_derived_screenshots", "_transcript_artifact_id"}
        }
        record["source_transcript_artifact_id"] = step.get("_transcript_artifact_id")
        return record

    @staticmethod
    def _to_note_record(note: dict) -> dict:
        return {key: value for key, value in note.items() if key != "_transcript_artifact_id"}


class FailureStage:
    """Persist failure state for background generation errors."""

    @staticmethod
    def mark_failed(db, session_id: str, detail: str | None = None) -> None:  # type: ignore[no-untyped-def]
        from app.models.draft_session import DraftSessionModel

        with bind_log_context(stage="failure"):
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
            logger.error(
                "Failure stage persisted draft generation error",
                extra={"event": "draft_generation.stage_failed", "failure_detail": failure_detail},
            )
