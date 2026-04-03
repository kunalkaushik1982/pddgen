from __future__ import annotations

import json
from collections import Counter
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Mapping, TypedDict, cast

from worker import bootstrap as _bootstrap  # noqa: F401
from app.core.observability import bind_log_context, get_logger
from sqlalchemy import delete, select

from app.models.artifact import ArtifactModel
from app.models.process_group import ProcessGroupModel
from app.models.process_note import ProcessNoteModel
from app.models.process_step import ProcessStepModel
from app.models.process_step_screenshot import ProcessStepScreenshotModel
from app.models.process_step_screenshot_candidate import ProcessStepScreenshotCandidateModel
from app.services.action_log_service import ActionLogService
from app.services.step_extraction import StepExtractionService
from app.services.transcript_intelligence import TranscriptIntelligenceService
from worker.services.ai_transcript_interpreter import AITranscriptInterpreter
from worker.services.draft_generation.stage_context import DraftGenerationContext
from worker.services.generation_types import NoteRecord, StepRecord
from worker.services.workflow_intelligence.segmentation_service import EvidenceSegmentationService
from worker.services.media.transcript_normalizer import TranscriptNormalizer

if TYPE_CHECKING:
    from app.models.draft_session import DraftSessionModel

logger = get_logger(__name__)


class _TranscriptSummaryBuckets(TypedDict):
    transcript_name: str
    top_actors: Counter[str]
    top_objects: Counter[str]
    top_systems: Counter[str]
    top_goals: Counter[str]
    top_rules: Counter[str]


class SessionPreparationStage:
    """Load session inputs and clear stale generated entities."""

    def load_and_prepare(self, db: Any, session: DraftSessionModel) -> DraftGenerationContext:
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

    def run(self, db: Any, context: DraftGenerationContext) -> None:
        from worker.services.draft_generation.support import extract_transcript_timestamps, timestamp_to_seconds

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
                    typed_steps = self._coerce_step_records(interpretation.steps)
                    typed_notes = self._coerce_note_records(interpretation.notes)
                    transcript_timestamps = extract_transcript_timestamps(normalized_text)
                    for index, step in enumerate(typed_steps):
                        inferred_start = transcript_timestamps[index] if index < len(transcript_timestamps) else (transcript_timestamps[-1] if transcript_timestamps else "")
                        inferred_end = transcript_timestamps[index + 1] if transcript_timestamps and (index + 1) < len(transcript_timestamps) else inferred_start
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
                        step["_transcript_artifact_id"] = transcript.id
                        step["process_group_id"] = context.default_process_group_id
                        step["meeting_id"] = getattr(transcript, "meeting_id", None)
                    context.all_steps.extend(typed_steps)
                    context.steps_by_transcript.setdefault(transcript.id, []).extend(typed_steps)
                    for note in typed_notes:
                        note["_transcript_artifact_id"] = transcript.id
                        note["process_group_id"] = context.default_process_group_id
                        note["meeting_id"] = getattr(transcript, "meeting_id", None)
                    context.all_notes.extend(typed_notes)
                    context.notes_by_transcript.setdefault(transcript.id, []).extend(typed_notes)
                    continue

                transcript_steps = self._coerce_step_records(self.step_extractor.extract_steps(
                    transcript_artifact_id=transcript.id,
                    transcript_text=normalized_text,
                ))
                for step in transcript_steps:
                    step["_transcript_artifact_id"] = transcript.id
                    step["process_group_id"] = context.default_process_group_id
                    step["meeting_id"] = getattr(transcript, "meeting_id", None)
                context.all_steps.extend(transcript_steps)
                context.steps_by_transcript.setdefault(transcript.id, []).extend(transcript_steps)
                transcript_notes = self._coerce_note_records(self.note_extractor.extract_notes(
                    transcript_artifact_id=transcript.id,
                    transcript_text=normalized_text,
                ))
                for note in transcript_notes:
                    note["_transcript_artifact_id"] = transcript.id
                    note["process_group_id"] = context.default_process_group_id
                    note["meeting_id"] = getattr(transcript, "meeting_id", None)
                context.all_notes.extend(transcript_notes)
                context.notes_by_transcript.setdefault(transcript.id, []).extend(transcript_notes)

            logger.info(
                "Transcript interpretation completed",
                extra={"event": "draft_generation.stage_completed", "step_count": len(context.all_steps), "note_count": len(context.all_notes)},
            )

    @staticmethod
    def _coerce_step_records(steps: Sequence[Mapping[str, object]]) -> list[StepRecord]:
        return [cast(StepRecord, step) for step in steps]

    @staticmethod
    def _coerce_note_records(notes: Sequence[Mapping[str, object]]) -> list[NoteRecord]:
        return [cast(NoteRecord, note) for note in notes]


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

    def run(self, db: Any, context: DraftGenerationContext) -> None:
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
        enrichment_confidence_counts = Counter(segment.enrichment.confidence for segment in context.evidence_segments if segment.enrichment is not None)
        enrichment_source_counts = Counter(segment.enrichment.enrichment_source for segment in context.evidence_segments if segment.enrichment is not None)
        boundary_decision_counts = Counter(decision.decision for decision in context.workflow_boundary_decisions)
        boundary_confidence_counts = Counter(decision.confidence for decision in context.workflow_boundary_decisions)
        boundary_source_counts = Counter(decision.decision_source for decision in context.workflow_boundary_decisions)
        boundary_conflict_counts = Counter("conflict" if decision.conflict_detected else "non_conflict" for decision in context.workflow_boundary_decisions)
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
        return {
            "conclusion": f"Built {len(context.evidence_segments)} evidence segment(s) across {len(context.transcript_artifacts)} transcript(s). Boundary classifier produced {len(context.workflow_boundary_decisions)} adjacent decision(s).",
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
            "sample_segments": [],
        }
