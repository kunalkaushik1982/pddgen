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


class ArtifactResponse(BaseModel):
    """Uploaded artifact response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
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


class ProcessStepResponse(BaseModel):
    """Process step response for draft session retrieval."""

    model_config = ConfigDict(from_attributes=True)

    id: str
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
    edited_by_ba: bool


class ProcessNoteResponse(BaseModel):
    """Business rule or note response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
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


class DraftSessionResponse(BaseModel):
    """Full draft session response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    status: str
    owner_id: str
    created_at: datetime
    updated_at: datetime
    artifacts: list[ArtifactResponse]
    process_steps: list[ProcessStepResponse]
    process_notes: list[ProcessNoteResponse]
    output_documents: list[OutputDocumentResponse]
