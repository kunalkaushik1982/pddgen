r"""
Purpose: Admin-only routes for user and job visibility.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\api\routes\admin.py
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import get_current_admin_user
from app.services.pipeline_orchestrator import PipelineOrchestratorService
from app.core.config import get_settings
from app.db.session import get_db_session
from app.models.draft_session import DraftSessionModel
from app.models.user import UserModel
from app.schemas.admin import AdminUserListItemResponse
from app.schemas.draft_session import DraftSessionListItemResponse
from app.services.mappers import map_draft_session_list_item


router = APIRouter(prefix="/admin", tags=["admin"])
settings = get_settings()


@router.get("/users", response_model=list[AdminUserListItemResponse])
def list_users(
    db: Annotated[Session, Depends(get_db_session)],
    _current_admin: Annotated[UserModel, Depends(get_current_admin_user)],
) -> list[AdminUserListItemResponse]:
    """Return admin-visible summaries for all users."""
    users = list(db.execute(select(UserModel).order_by(UserModel.created_at.desc())).scalars().all())
    total_jobs_rows = db.execute(
        select(DraftSessionModel.owner_id, func.count(DraftSessionModel.id)).group_by(DraftSessionModel.owner_id)
    ).all()
    active_jobs_rows = db.execute(
        select(DraftSessionModel.owner_id, func.count(DraftSessionModel.id))
        .where(DraftSessionModel.status.in_(("draft", "processing", "review")))
        .group_by(DraftSessionModel.owner_id)
    ).all()
    total_jobs_by_owner = {owner_id: count for owner_id, count in total_jobs_rows}
    active_jobs_by_owner = {owner_id: count for owner_id, count in active_jobs_rows}

    return [
        AdminUserListItemResponse(
            id=user.id,
            username=user.username,
            created_at=user.created_at,
            is_admin=user.username in settings.admin_usernames,
            total_jobs=total_jobs_by_owner.get(user.username, 0),
            active_jobs=active_jobs_by_owner.get(user.username, 0),
        )
        for user in users
    ]


@router.get("/jobs", response_model=list[DraftSessionListItemResponse])
def list_jobs(
    db: Annotated[Session, Depends(get_db_session)],
    _current_admin: Annotated[UserModel, Depends(get_current_admin_user)],
) -> list[DraftSessionListItemResponse]:
    """Return all draft sessions across all users."""
    statement = (
        select(DraftSessionModel)
        .options(
            selectinload(DraftSessionModel.artifacts),
            selectinload(DraftSessionModel.action_logs),
        )
        .order_by(DraftSessionModel.updated_at.desc())
    )
    sessions = list(db.execute(statement).scalars().all())
    for session in sessions:
        PipelineOrchestratorService.reconcile_stale_screenshot_processing_if_needed(db, session)
    return [map_draft_session_list_item(session) for session in sessions]
