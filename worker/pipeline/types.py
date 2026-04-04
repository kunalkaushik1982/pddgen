from __future__ import annotations

from typing import TYPE_CHECKING, Any, NotRequired, TypedDict

if TYPE_CHECKING:
    from app.models.artifact import ArtifactModel
else:
    ArtifactModel = Any


class ScreenshotCandidateRecord(TypedDict):
    artifact: ArtifactModel
    sequence_number: int
    timestamp: str
    source_role: str
    selection_method: str
    offset_seconds: int
    file_size: int


class DerivedScreenshotRecord(TypedDict):
    artifact: ArtifactModel
    role: str
    sequence_number: int
    timestamp: str
    selection_method: str
    is_primary: bool


class StepRecord(TypedDict):
    id: str
    process_group_id: str | None
    meeting_id: str | None
    step_number: int
    application_name: str
    action_text: str
    source_data_note: str
    timestamp: str
    start_timestamp: str
    end_timestamp: str
    supporting_transcript_text: str
    screenshot_id: str
    confidence: str
    evidence_references: str
    edited_by_ba: bool
    _transcript_artifact_id: NotRequired[str | None]
    _candidate_screenshots: NotRequired[list[ScreenshotCandidateRecord]]
    _derived_screenshots: NotRequired[list[DerivedScreenshotRecord]]


class NoteRecord(TypedDict):
    text: str
    related_step_ids: str
    evidence_reference_ids: str
    confidence: str
    inference_type: str
    process_group_id: NotRequired[str | None]
    meeting_id: NotRequired[str | None]
    _transcript_artifact_id: NotRequired[str | None]
