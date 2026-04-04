from __future__ import annotations

import json
from collections import Counter
from typing import TypedDict

from app.core.observability import bind_log_context, get_logger
from app.services.action_log_service import ActionLogService
from worker.services.draft_generation.stage_context import DraftGenerationContext
from worker.services.media.transcript_normalizer import TranscriptNormalizer
from worker.services.workflow_intelligence.segmentation_service import EvidenceSegmentationService

logger = get_logger(__name__)


class TranscriptSegmentationSummary(TypedDict):
    transcript_name: str
    top_actors: Counter[str]
    top_objects: Counter[str]
    top_systems: Counter[str]
    top_goals: Counter[str]
    top_rules: Counter[str]


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

    def _build_segmentation_metadata(self, context: DraftGenerationContext) -> dict[str, object]:
        segment_method_counts = Counter(segment.segmentation_method for segment in context.evidence_segments)
        enrichment_confidence_counts = Counter(segment.enrichment.confidence for segment in context.evidence_segments if segment.enrichment is not None)
        enrichment_source_counts = Counter(segment.enrichment.enrichment_source for segment in context.evidence_segments if segment.enrichment is not None)
        boundary_decision_counts = Counter(decision.decision for decision in context.workflow_boundary_decisions)
        boundary_confidence_counts = Counter(decision.confidence for decision in context.workflow_boundary_decisions)
        boundary_source_counts = Counter(decision.decision_source for decision in context.workflow_boundary_decisions)
        boundary_conflict_counts = Counter("conflict" if decision.conflict_detected else "non_conflict" for decision in context.workflow_boundary_decisions)
        transcript_summaries: dict[str, TranscriptSegmentationSummary] = {}
        transcript_names = {artifact.id: artifact.name for artifact in context.transcript_artifacts}
        for segment in context.evidence_segments:
            summary = transcript_summaries.setdefault(
                segment.transcript_artifact_id,
                {
                    "transcript_name": transcript_names.get(segment.transcript_artifact_id, segment.transcript_artifact_id),
                    "top_actors": Counter(),
                    "top_objects": Counter(),
                    "top_systems": Counter(),
                    "top_goals": Counter(),
                    "top_rules": Counter(),
                },
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
