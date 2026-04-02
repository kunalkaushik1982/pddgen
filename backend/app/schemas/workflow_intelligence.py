r"""
Purpose: Foundation workflow-intelligence contracts for segment-aware processing.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\schemas\workflow_intelligence.py
"""

from pydantic import BaseModel

from app.schemas.common import ConfidenceLevel, ResolutionStatus


class SemanticEnrichmentResponse(BaseModel):
    """Derived semantic labels for one evidence segment."""

    actor: str | None = None
    system_name: str | None = None
    action_verb: str | None = None
    business_object: str | None = None
    workflow_goal: str | None = None
    confidence: ConfidenceLevel = "unknown"
    resolution_status: ResolutionStatus = "auto_resolved"


class EvidenceSegmentResponse(BaseModel):
    """Timestamped evidence segment used for workflow-boundary reasoning."""

    id: str
    transcript_artifact_id: str
    meeting_id: str | None = None
    segment_order: int
    text: str
    start_timestamp: str | None = None
    end_timestamp: str | None = None
    segmentation_method: str = "transcript_chunk"
    confidence: ConfidenceLevel = "unknown"
    enrichment: SemanticEnrichmentResponse | None = None


class WorkflowBoundaryDecisionResponse(BaseModel):
    """Decision describing whether adjacent segments belong to one workflow."""

    left_segment_id: str
    right_segment_id: str
    decision: str
    confidence: ConfidenceLevel = "unknown"
    reason: str = ""
    resolution_status: ResolutionStatus = "auto_resolved"
