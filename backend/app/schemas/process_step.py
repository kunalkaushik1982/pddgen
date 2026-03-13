r"""
Purpose: API schemas for process step review and editing.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\schemas\process_step.py
"""

from pydantic import BaseModel, Field

from app.schemas.common import ConfidenceLevel


class ProcessStepUpdateRequest(BaseModel):
    """Request payload for moderate BA edits to a process step."""

    application_name: str | None = Field(default=None, max_length=255)
    action_text: str | None = Field(default=None, min_length=1)
    source_data_note: str | None = None
    timestamp: str | None = None
    start_timestamp: str | None = None
    end_timestamp: str | None = None
    supporting_transcript_text: str | None = None
    screenshot_id: str | None = None
    confidence: ConfidenceLevel | None = None
    edited_by_ba: bool = True


class StepScreenshotUpdateRequest(BaseModel):
    """Request payload for updating one screenshot slot on a process step."""

    is_primary: bool | None = None
    role: str | None = None


class CandidateScreenshotSelectRequest(BaseModel):
    """Request payload for selecting one generated candidate screenshot."""

    is_primary: bool | None = None
    role: str | None = None
