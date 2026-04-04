r"""
Purpose: Shared generation context for worker draft-generation stages.
Full filepath: C:\Users\work\Documents\PddGenerator\worker\pipeline\stages\stage_context.py
"""

from dataclasses import dataclass, field

from app.models.artifact import ArtifactModel
from app.models.draft_session import DraftSessionModel
from app.models.process_step import ProcessStepModel
from worker.grouping import EvidenceSegment, WorkflowBoundaryDecision
from worker.grouping.grouping_models import ProcessGroupWorkItem
from worker.pipeline.types import NoteRecord, StepRecord


@dataclass(frozen=True, slots=True)
class SessionInputs:
    """Frozen initial session configuration for a draft-generation run."""

    session_id: str
    session: DraftSessionModel
    document_type: str = "pdd"
    transcript_artifacts: list[ArtifactModel] = field(default_factory=list)
    video_artifacts: list[ArtifactModel] = field(default_factory=list)


@dataclass(slots=True)
class DraftGenerationContext:
    """Carry mutable generation state between worker stages."""

    inputs: SessionInputs
    normalized_transcripts: dict[str, str] = field(default_factory=dict)
    evidence_segments: list[EvidenceSegment] = field(default_factory=list)
    workflow_boundary_decisions: list[WorkflowBoundaryDecision] = field(default_factory=list)
    default_process_group_id: str | None = None
    process_groups: list[ProcessGroupWorkItem] = field(default_factory=list)
    all_steps: list[StepRecord] = field(default_factory=list)
    all_notes: list[NoteRecord] = field(default_factory=list)
    steps_by_transcript: dict[str, list[StepRecord]] = field(default_factory=dict)
    notes_by_transcript: dict[str, list[NoteRecord]] = field(default_factory=dict)
    persisted_step_models: list[ProcessStepModel] = field(default_factory=list)
    screenshot_artifacts: list[ArtifactModel] = field(default_factory=list)
    overview_diagram_json: str = ""
    detailed_diagram_json: str = ""
    selected_screenshot_count: int = 0
