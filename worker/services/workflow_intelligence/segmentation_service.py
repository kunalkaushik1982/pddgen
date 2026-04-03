r"""
Purpose: Lightweight transcript segmentation and semantic enrichment for workflow-intelligence groundwork.
Full filepath: C:\Users\work\Documents\PddGenerator\worker\services\evidence_segmentation_service.py
"""

from __future__ import annotations

from worker.services.workflow_intelligence import EvidenceSegment, WorkflowBoundaryDecision
from worker.services.workflow_intelligence.segmentation_ai_strategies import (
    AISemanticEnrichmentStrategy,
    AIWorkflowBoundaryStrategy,
)
from worker.services.workflow_intelligence.segmentation_heuristics import (
    HeuristicSemanticEnrichmentStrategy,
    HeuristicWorkflowBoundaryStrategy,
    ParagraphTranscriptSegmentationStrategy,
)
from worker.services.workflow_intelligence.strategy_interfaces import WorkflowIntelligenceStrategySet


class EvidenceSegmentationService:
    """Orchestrate segmentation, enrichment, and boundary detection via explicit strategies."""

    def __init__(
        self,
        *,
        strategy_set: WorkflowIntelligenceStrategySet,
    ) -> None:
        self.segmenter = strategy_set.segmenter
        self.enricher = strategy_set.enricher
        self.boundary_detector = strategy_set.boundary_detector

    def segment_transcript(
        self,
        *,
        transcript_artifact_id: str,
        meeting_id: str | None,
        transcript_text: str,
    ) -> list[EvidenceSegment]:
        """Produce ordered evidence segments from one normalized transcript."""
        segments = self.segmenter.segment(
            transcript_artifact_id=transcript_artifact_id,
            meeting_id=meeting_id,
            transcript_text=transcript_text,
        )
        for segment in segments:
            segment.enrichment = self.enricher.enrich(segment)
        return segments

    def infer_boundary_decisions(self, segments: list[EvidenceSegment]) -> list[WorkflowBoundaryDecision]:
        """Produce a first-pass same-vs-new workflow decision between adjacent segments."""
        return [self.boundary_detector.decide(left, right) for left, right in zip(segments, segments[1:])]
