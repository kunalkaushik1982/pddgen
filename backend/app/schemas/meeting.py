r"""
Purpose: API schemas for session meetings.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\schemas\meeting.py
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreateMeetingRequest(BaseModel):
    """Create a new meeting under a session."""

    title: str = Field(default="", max_length=255)
    meeting_date: datetime | None = None


class UpdateMeetingRequest(BaseModel):
    """Update meeting metadata."""

    title: str | None = Field(default=None, max_length=255)
    meeting_date: datetime | None = None
    order_index: int | None = None


class MeetingResponse(BaseModel):
    """Meeting metadata returned to the frontend."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    title: str
    meeting_date: datetime | None
    uploaded_at: datetime
    order_index: int | None


class ReorderMeetingsRequest(BaseModel):
    """Reorder meetings within one session."""

    meeting_ids: list[str] = Field(min_length=1)

