r"""
Purpose: Admin-only routes for user and job visibility.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\api\routes\admin.py
"""

from typing import Annotated
import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import get_current_admin_user
from app.services.generation.pipeline_orchestrator import PipelineOrchestratorService
from app.core.config import get_settings
from app.db.session import get_db_session
from app.models.draft_session import DraftSessionModel
from app.models.user import UserModel
from app.schemas.admin import (
    AdminPreferencesResponse,
    AdminPreferencesUpdateRequest,
    AdminSessionMetricsResponse,
    AdminUserListItemResponse,
    AdminUserQuotaUpdateRequest,
)
from app.schemas.draft_session import DraftSessionListItemResponse
from app.services.draft_session.mappers import map_draft_session_list_item
from app.services.admin.usage_metrics_service import list_admin_session_metrics
from app.services.draft_session.user_quota_service import effective_limits


router = APIRouter(prefix="/admin", tags=["admin"])
settings = get_settings()
DEFAULT_SESSION_METRICS_VISIBLE_COLUMNS = [
    "session",
    "owner",
    "status",
    "total_estimated_cost_inr",
    "updated_at",
]


def _load_admin_preferences(user: UserModel) -> dict[str, object]:
    raw = (user.admin_preferences_json or "").strip()
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _build_admin_preferences_response(user: UserModel) -> AdminPreferencesResponse:
    preferences = _load_admin_preferences(user)
    visible_columns = preferences.get("session_metrics_visible_columns")
    if not isinstance(visible_columns, list) or not all(isinstance(item, str) for item in visible_columns):
        visible_columns = DEFAULT_SESSION_METRICS_VISIBLE_COLUMNS
    return AdminPreferencesResponse(session_metrics_visible_columns=list(visible_columns))


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

    out: list[AdminUserListItemResponse] = []
    for user in users:
        life_cap, day_cap = effective_limits(settings, user)
        out.append(
            AdminUserListItemResponse(
                id=user.id,
                username=user.username,
                created_at=user.created_at,
                is_admin=user.username in settings.admin_usernames,
                total_jobs=total_jobs_by_owner.get(user.username, 0),
                active_jobs=active_jobs_by_owner.get(user.username, 0),
                quota_lifetime_bonus=int(user.quota_lifetime_bonus or 0),
                quota_daily_bonus=int(user.quota_daily_bonus or 0),
                job_usage_lifetime=int(user.job_usage_lifetime or 0),
                job_usage_daily=int(user.job_usage_daily or 0),
                effective_lifetime_cap=life_cap,
                effective_daily_cap=day_cap,
            )
        )
    return out


@router.patch("/users/{user_id}/quota", response_model=AdminUserListItemResponse)
def update_user_quota(
    user_id: str,
    payload: AdminUserQuotaUpdateRequest,
    db: Annotated[Session, Depends(get_db_session)],
    _current_admin: Annotated[UserModel, Depends(get_current_admin_user)],
) -> AdminUserListItemResponse:
    """Set per-user quota bonuses (adds to global env defaults)."""
    user = db.get(UserModel, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if payload.quota_lifetime_bonus is None and payload.quota_daily_bonus is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide quota_lifetime_bonus and/or quota_daily_bonus.",
        )
    if payload.quota_lifetime_bonus is not None:
        user.quota_lifetime_bonus = payload.quota_lifetime_bonus
    if payload.quota_daily_bonus is not None:
        user.quota_daily_bonus = payload.quota_daily_bonus
    db.add(user)
    db.commit()
    db.refresh(user)
    total_jobs_rows = db.execute(
        select(func.count(DraftSessionModel.id)).where(DraftSessionModel.owner_id == user.username)
    ).scalar_one()
    active_jobs_rows = db.execute(
        select(func.count(DraftSessionModel.id))
        .where(DraftSessionModel.owner_id == user.username)
        .where(DraftSessionModel.status.in_(("draft", "processing", "review")))
    ).scalar_one()
    life_cap, day_cap = effective_limits(settings, user)
    return AdminUserListItemResponse(
        id=user.id,
        username=user.username,
        created_at=user.created_at,
        is_admin=user.username in settings.admin_usernames,
        total_jobs=int(total_jobs_rows or 0),
        active_jobs=int(active_jobs_rows or 0),
        quota_lifetime_bonus=int(user.quota_lifetime_bonus or 0),
        quota_daily_bonus=int(user.quota_daily_bonus or 0),
        job_usage_lifetime=int(user.job_usage_lifetime or 0),
        job_usage_daily=int(user.job_usage_daily or 0),
        effective_lifetime_cap=life_cap,
        effective_daily_cap=day_cap,
    )


@router.get("/preferences", response_model=AdminPreferencesResponse)
def get_admin_preferences(
    _db: Annotated[Session, Depends(get_db_session)],
    current_admin: Annotated[UserModel, Depends(get_current_admin_user)],
) -> AdminPreferencesResponse:
    """Return persisted admin-console preferences for the current admin user."""
    return _build_admin_preferences_response(current_admin)


@router.put("/preferences", response_model=AdminPreferencesResponse)
def update_admin_preferences(
    payload: AdminPreferencesUpdateRequest,
    db: Annotated[Session, Depends(get_db_session)],
    current_admin: Annotated[UserModel, Depends(get_current_admin_user)],
) -> AdminPreferencesResponse:
    """Persist admin-console preferences for the current admin user."""
    current_admin.admin_preferences_json = json.dumps(
        {"session_metrics_visible_columns": payload.session_metrics_visible_columns}
    )
    db.add(current_admin)
    db.commit()
    db.refresh(current_admin)
    return _build_admin_preferences_response(current_admin)


@router.get("/metrics/sessions", response_model=list[AdminSessionMetricsResponse])
def list_session_metrics(
    db: Annotated[Session, Depends(get_db_session)],
    _current_admin: Annotated[UserModel, Depends(get_current_admin_user)],
) -> list[AdminSessionMetricsResponse]:
    """Per-session LLM token totals, estimated cost, and background job wall time."""
    return list_admin_session_metrics(db)


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
