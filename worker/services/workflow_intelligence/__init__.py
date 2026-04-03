r"""
Purpose: Workflow-intelligence foundation contracts for worker-side segment-aware processing.
Full filepath: C:\Users\work\Documents\PddGenerator\worker\services\workflow_intelligence.py
"""

from dataclasses import dataclass, field


@dataclass(slots=True)
class SemanticEnrichment:
    """Derived semantic labels for one evidence segment."""

    actor: str | None = None
    actor_role: str | None = None
    system_name: str | None = None
    action_verb: str | None = None
    action_type: str | None = None
    business_object: str | None = None
    workflow_goal: str | None = None
    rule_hints: list[str] = field(default_factory=list)
    domain_terms: list[str] = field(default_factory=list)
    confidence: str = "unknown"
    enrichment_source: str = "heuristic"
    resolution_status: str = "auto_resolved"


@dataclass(slots=True)
class EvidenceSegment:
    """Timestamped segment of transcript evidence for future workflow reasoning."""

    id: str
    transcript_artifact_id: str
    meeting_id: str | None
    segment_order: int
    text: str
    start_timestamp: str | None = None
    end_timestamp: str | None = None
    segmentation_method: str = "transcript_chunk"
    confidence: str = "unknown"
    enrichment: SemanticEnrichment | None = None


@dataclass(slots=True)
class WorkflowBoundaryDecision:
    """Decision for adjacent evidence segments."""

    left_segment_id: str
    right_segment_id: str
    decision: str
    confidence: str = "unknown"
    reason: str = ""
    decision_source: str = "heuristic"
    heuristic_decision: str | None = None
    heuristic_confidence: str | None = None
    ai_decision: str | None = None
    ai_confidence: str | None = None
    conflict_detected: bool = False
    resolution_status: str = "auto_resolved"
