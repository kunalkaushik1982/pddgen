r"""
Purpose: Typed strategy contracts for workflow-intelligence stage composition.
Full filepath: C:\Users\work\Documents\PddGenerator\worker\grouping\strategy_interfaces.py
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from . import EvidenceSegment, SemanticEnrichment, WorkflowBoundaryDecision


class TranscriptSegmentationStrategy(Protocol):
    """Create ordered raw evidence segments from one normalized transcript."""

    strategy_key: str

    def segment(
        self,
        *,
        transcript_artifact_id: str,
        meeting_id: str | None,
        transcript_text: str,
    ) -> list[EvidenceSegment]:
        """Return ordered evidence segments without requiring persistence."""
        ...


class SegmentEnrichmentStrategy(Protocol):
    """Enrich one evidence segment with workflow-relevant semantic labels."""

    strategy_key: str

    def enrich(self, segment: EvidenceSegment) -> SemanticEnrichment:
        """Return semantic enrichment for one transcript segment."""
        ...


class WorkflowBoundaryStrategy(Protocol):
    """Decide whether two adjacent segments belong to the same workflow."""

    strategy_key: str

    def decide(self, left: EvidenceSegment, right: EvidenceSegment) -> WorkflowBoundaryDecision:
        """Return a first-pass workflow-boundary decision."""
        ...


@dataclass(slots=True)
class WorkflowIntelligenceStrategySet:
    """Resolved strategy bundle for segmentation, enrichment, and boundary detection."""

    segmenter: TranscriptSegmentationStrategy
    enricher: SegmentEnrichmentStrategy
    boundary_detector: WorkflowBoundaryStrategy
