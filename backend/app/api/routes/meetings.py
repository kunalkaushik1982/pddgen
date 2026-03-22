r"""
Purpose: API routes for managing meetings under a draft session.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\api\routes\meetings.py
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_meeting_service
from app.db.session import get_db_session
from app.models.user import UserModel
from app.schemas.meeting import CreateMeetingRequest, MeetingResponse, ReorderMeetingsRequest, UpdateMeetingRequest
from app.services.meeting_service import MeetingService


router = APIRouter(prefix="/draft-sessions/{session_id}/meetings", tags=["meetings"])


@router.get("", response_model=list[MeetingResponse])
def list_meetings(
    session_id: str,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[MeetingService, Depends(get_meeting_service)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> list[MeetingResponse]:
    meetings = service.list_meetings(db, session_id=session_id, owner_id=current_user.username)
    return [MeetingResponse.model_validate(meeting) for meeting in meetings]


@router.post("", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
def create_meeting(
    session_id: str,
    payload: CreateMeetingRequest,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[MeetingService, Depends(get_meeting_service)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> MeetingResponse:
    meeting = service.create_meeting(
        db,
        session_id=session_id,
        owner_id=current_user.username,
        title=payload.title,
        meeting_date=payload.meeting_date,
    )
    return MeetingResponse.model_validate(meeting)


@router.patch("/reorder", response_model=list[MeetingResponse])
def reorder_meetings(
    session_id: str,
    payload: ReorderMeetingsRequest,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[MeetingService, Depends(get_meeting_service)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> list[MeetingResponse]:
    meetings = service.reorder_meetings(
        db,
        session_id=session_id,
        owner_id=current_user.username,
        meeting_ids=payload.meeting_ids,
    )
    return [MeetingResponse.model_validate(meeting) for meeting in meetings]


@router.patch("/{meeting_id}", response_model=MeetingResponse)
def update_meeting(
    session_id: str,
    meeting_id: str,
    payload: UpdateMeetingRequest,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[MeetingService, Depends(get_meeting_service)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> MeetingResponse:
    fields = payload.model_fields_set
    meeting = service.update_meeting(
        db,
        session_id=session_id,
        meeting_id=meeting_id,
        owner_id=current_user.username,
        title=payload.title if "title" in fields else None,
        meeting_date=payload.meeting_date,
        set_meeting_date="meeting_date" in fields,
        order_index=payload.order_index if "order_index" in fields else None,
        set_order_index="order_index" in fields,
    )
    return MeetingResponse.model_validate(meeting)

