r"""
Purpose: Shared generation context for worker draft-generation stages.
Full filepath: C:\Users\work\Documents\PddGenerator\worker\services\draft_generation_stage_context.py
"""

from dataclasses import dataclass, field
from typing import Any

from app.models.artifact import ArtifactModel
from app.models.draft_session import DraftSessionModel
from app.models.process_step import ProcessStepModel


@dataclass(slots=True)
class DraftGenerationContext:
    """Carry mutable generation state between worker stages."""

    session_id: str
    session: DraftSessionModel
    transcript_artifacts: list[ArtifactModel] = field(default_factory=list)
    video_artifacts: list[ArtifactModel] = field(default_factory=list)
    default_process_group_id: str | None = None
    process_groups: list[Any] = field(default_factory=list)
    all_steps: list[dict] = field(default_factory=list)
    all_notes: list[dict] = field(default_factory=list)
    steps_by_transcript: dict[str, list[dict]] = field(default_factory=dict)
    notes_by_transcript: dict[str, list[dict]] = field(default_factory=dict)
    persisted_step_models: list[ProcessStepModel] = field(default_factory=list)
    screenshot_artifacts: list[ArtifactModel] = field(default_factory=list)
    overview_diagram_json: str = ""
    detailed_diagram_json: str = ""
