r"""
Purpose: API schemas for draft session payloads.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\schemas\draft_session.py
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import ArtifactKind, ConfidenceLevel, EvidenceReference


class CreateDraftSessionRequest(BaseModel):
    """Request payload for creating a draft session."""

    title: str = Field(default="Untitled PDD Session", min_length=1, max_length=255)
    owner_id: str = Field(default="pilot-user", min_length=1, max_length=255)
    diagram_type: str = Field(default="flowchart", min_length=1, max_length=50)


class ArtifactResponse(BaseModel):
    """Uploaded artifact response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    meeting_id: str | None = None
    name: str
    kind: ArtifactKind
    storage_path: str
    content_type: str | None
    size_bytes: int
    created_at: datetime


class StepScreenshotResponse(BaseModel):
    """Ordered screenshot evidence for one process step."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    artifact_id: str
    role: str
    sequence_number: int
    timestamp: str
    selection_method: str
    is_primary: bool
    artifact: ArtifactResponse


class CandidateScreenshotResponse(BaseModel):
    """Candidate screenshot evidence available for manual BA selection."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    artifact_id: str
    sequence_number: int
    timestamp: str
    source_role: str
    selection_method: str
    is_selected: bool
    artifact: ArtifactResponse


class ProcessStepResponse(BaseModel):
    """Process step response for draft session retrieval."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    process_group_id: str | None = None
    meeting_id: str | None = None
    step_number: int
    application_name: str
    action_text: str
    source_data_note: str
    timestamp: str
    start_timestamp: str
    end_timestamp: str
    supporting_transcript_text: str
    screenshot_id: str
    confidence: ConfidenceLevel
    evidence_references: list[EvidenceReference]
    screenshots: list[StepScreenshotResponse]
    candidate_screenshots: list[CandidateScreenshotResponse]
    edited_by_ba: bool


class ProcessNoteResponse(BaseModel):
    """Business rule or note response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    process_group_id: str | None = None
    meeting_id: str | None = None
    text: str
    related_step_ids: list[str]
    evidence_reference_ids: list[str]
    confidence: ConfidenceLevel
    inference_type: str


class OutputDocumentResponse(BaseModel):
    """Generated DOCX response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    kind: str
    storage_path: str
    exported_at: datetime


class ProcessGroupResponse(BaseModel):
    """Logical process group persisted inside one session."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    title: str
    canonical_slug: str
    status: str
    display_order: int
    summary_text: str
    overview_diagram_json: str
    detailed_diagram_json: str


class ActionLogResponse(BaseModel):
    """Meaningful activity event for one draft session."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    event_type: str
    title: str
    detail: str
    actor: str
    created_at: datetime


class DraftSessionResponse(BaseModel):
    """Full draft session response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    status: str
    owner_id: str
    diagram_type: str
    created_at: datetime
    updated_at: datetime
    process_groups: list[ProcessGroupResponse]
    artifacts: list[ArtifactResponse]
    process_steps: list[ProcessStepResponse]
    process_notes: list[ProcessNoteResponse]
    output_documents: list[OutputDocumentResponse]
    action_logs: list[ActionLogResponse]


class DraftSessionListItemResponse(BaseModel):
    """Compact draft session response for history lists."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    status: str
    owner_id: str
    diagram_type: str
    created_at: datetime
    updated_at: datetime
    latest_stage_title: str = ""
    latest_stage_detail: str = ""
    failure_detail: str = ""
    resume_ready: bool = False
    can_retry: bool = False


class SessionQuestionRequest(BaseModel):
    """Question asked against one session's evidence."""

    question: str = Field(min_length=1, max_length=4000)
    process_group_id: str | None = None


class SessionAnswerCitationResponse(BaseModel):
    """Citation used in one grounded session answer."""

    id: str
    source_type: str
    title: str
    snippet: str


class SessionAnswerResponse(BaseModel):
    """Grounded answer for one session question."""

    answer: str
    confidence: str
    citations: list[SessionAnswerCitationResponse]


class DiagramNodeResponse(BaseModel):
    """Flowchart node response for frontend-driven diagram rendering."""

    id: str
    label: str
    category: str
    step_range: str
    width: float | None = None
    height: float | None = None


class DiagramEdgeResponse(BaseModel):
    """Flowchart edge response for frontend-driven diagram rendering."""

    id: str
    source: str
    target: str
    label: str = ""
    source_handle: str | None = None
    target_handle: str | None = None


class DiagramModelResponse(BaseModel):
    """Diagram model payload used by the frontend preview renderer."""

    diagram_type: str
    view_type: str
    title: str
    nodes: list[DiagramNodeResponse]
    edges: list[DiagramEdgeResponse]


class DiagramLayoutNodePosition(BaseModel):
    """Persisted diagram node position for one rendered node."""

    id: str
    x: float
    y: float
    label: str | None = None
    width: float | None = None
    height: float | None = None


class DiagramCanvasSettingsResponse(BaseModel):
    """Persisted canvas presentation settings for one diagram view."""

    theme: str = "dark"
    show_grid: bool = True
    grid_density: str = "medium"


class DiagramLayoutResponse(BaseModel):
    """Saved diagram layout response for one session view."""

    session_id: str
    process_group_id: str | None = None
    view_type: str
    nodes: list[DiagramLayoutNodePosition]
    export_preset: str = "balanced"
    canvas_settings: DiagramCanvasSettingsResponse = Field(default_factory=DiagramCanvasSettingsResponse)


class SaveDiagramLayoutRequest(BaseModel):
    """Request payload to persist draggable diagram node positions."""

    nodes: list[DiagramLayoutNodePosition]
    export_preset: str = "balanced"
    canvas_settings: DiagramCanvasSettingsResponse = Field(default_factory=DiagramCanvasSettingsResponse)


class SaveDiagramArtifactRequest(BaseModel):
    """Persist the browser-rendered diagram image used for export."""

    image_data_url: str


class SaveDiagramModelRequest(BaseModel):
    """Persist the edited diagram graph used by the frontend and export."""

    title: str
    view_type: str
    nodes: list[DiagramNodeResponse]
    edges: list[DiagramEdgeResponse]
