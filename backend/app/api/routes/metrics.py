r"""
Purpose: Authenticated metrics routes shared by normal users and admins.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\api\routes\metrics.py
"""

from typing import Annotated
import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.models.draft_session import DraftSessionModel
from app.models.user import UserModel
from app.schemas.admin import (
    AdminPreferencesResponse,
    AdminPreferencesUpdateRequest,
    AdminSessionMetricsResponse,
    MetricsOwnerOptionResponse,
)
from app.schemas.draft_session import DraftSessionListItemResponse
from app.services.draft_session.mappers import map_draft_session_list_item
from app.services.generation.pipeline_orchestrator import PipelineOrchestratorService
from app.services.admin.usage_metrics_service import list_admin_session_metrics


router = APIRouter(prefix="/metrics", tags=["metrics"])
DEFAULT_SESSION_METRICS_VISIBLE_COLUMNS = [
    "session",
    "owner",
    "status",
    "total_estimated_cost_inr",
    "updated_at",
]


def _is_admin(user: UserModel) -> bool:
    from app.core.config import get_settings

    return user.username in get_settings().admin_usernames


def _load_preferences(user: UserModel) -> dict[str, object]:
    raw = (user.admin_preferences_json or "").strip()
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _resolve_owner_scope(current_user: UserModel, requested_owner_id: str | None) -> str | None:
    if not _is_admin(current_user):
        return current_user.username
    if requested_owner_id in (None, "", "all"):
        return None
    return requested_owner_id


def _build_preferences_response(user: UserModel) -> AdminPreferencesResponse:
    preferences = _load_preferences(user)
    visible_columns = preferences.get("session_metrics_visible_columns")
    if not isinstance(visible_columns, list) or not all(isinstance(item, str) for item in visible_columns):
        visible_columns = DEFAULT_SESSION_METRICS_VISIBLE_COLUMNS
    selected_owner_id = preferences.get("metrics_selected_owner_id")
    if not isinstance(selected_owner_id, str) or not selected_owner_id.strip():
        selected_owner_id = "all" if _is_admin(user) else user.username
    if not _is_admin(user):
        selected_owner_id = user.username
    return AdminPreferencesResponse(
        session_metrics_visible_columns=list(visible_columns),
        metrics_selected_owner_id=selected_owner_id,
    )


@router.get("/preferences", response_model=AdminPreferencesResponse)
def get_metrics_preferences(
    _db: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> AdminPreferencesResponse:
    return _build_preferences_response(current_user)


@router.put("/preferences", response_model=AdminPreferencesResponse)
def update_metrics_preferences(
    payload: AdminPreferencesUpdateRequest,
    db: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> AdminPreferencesResponse:
    next_owner_id = payload.metrics_selected_owner_id
    if not _is_admin(current_user):
        next_owner_id = current_user.username
    current_user.admin_preferences_json = json.dumps(
        {
            "session_metrics_visible_columns": payload.session_metrics_visible_columns,
            "metrics_selected_owner_id": next_owner_id or "all",
        }
    )
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return _build_preferences_response(current_user)


@router.get("/owners", response_model=list[MetricsOwnerOptionResponse])
def list_metric_owners(
    db: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> list[MetricsOwnerOptionResponse]:
    if not _is_admin(current_user):
        return [MetricsOwnerOptionResponse(id=current_user.username, label=current_user.username)]
    users = list(db.execute(select(UserModel).order_by(UserModel.username.asc())).scalars().all())
    return [MetricsOwnerOptionResponse(id=user.username, label=user.username) for user in users]


@router.get("/sessions", response_model=list[AdminSessionMetricsResponse])
def list_session_metrics(
    owner_id: str | None = None,
    db: Annotated[Session, Depends(get_db_session)] = None,
    current_user: Annotated[UserModel, Depends(get_current_user)] = None,
) -> list[AdminSessionMetricsResponse]:
    return list_admin_session_metrics(db, owner_id=_resolve_owner_scope(current_user, owner_id))


@router.get("/jobs", response_model=list[DraftSessionListItemResponse])
def list_jobs(
    owner_id: str | None = None,
    db: Annotated[Session, Depends(get_db_session)] = None,
    current_user: Annotated[UserModel, Depends(get_current_user)] = None,
) -> list[DraftSessionListItemResponse]:
    statement = (
        select(DraftSessionModel)
        .options(
            selectinload(DraftSessionModel.artifacts),
            selectinload(DraftSessionModel.action_logs),
        )
        .order_by(DraftSessionModel.updated_at.desc())
    )
    resolved_owner_id = _resolve_owner_scope(current_user, owner_id)
    if resolved_owner_id:
        statement = statement.where(DraftSessionModel.owner_id == resolved_owner_id)
    sessions = list(db.execute(statement).scalars().all())
    for session in sessions:
        PipelineOrchestratorService.reconcile_stale_screenshot_processing_if_needed(db, session)
    return [map_draft_session_list_item(session) for session in sessions]
