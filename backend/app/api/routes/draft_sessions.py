r"""
Purpose: API routes for draft session retrieval and BA review actions.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\api\routes\draft_sessions.py
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_job_dispatcher_service, get_pipeline_orchestrator_service
from app.db.session import get_db_session
from app.models.draft_session import DraftSessionModel
from app.models.user import UserModel
from app.schemas.draft_session import DraftSessionListItemResponse, DraftSessionResponse, ProcessStepResponse
from app.schemas.process_step import CandidateScreenshotSelectRequest, ProcessStepUpdateRequest, StepScreenshotUpdateRequest
from app.models.artifact import ArtifactModel
from app.models.process_step_screenshot_candidate import ProcessStepScreenshotCandidateModel
from app.models.process_step_screenshot import ProcessStepScreenshotModel
from app.services.job_dispatcher import JobDispatcherService
from app.services.mappers import map_draft_session, map_draft_session_list_item, map_process_step
from app.services.pipeline_orchestrator import PipelineOrchestratorService

router = APIRouter(prefix="/draft-sessions", tags=["draft-sessions"])


@router.get("", response_model=list[DraftSessionListItemResponse])
def list_draft_sessions(
    db: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> list[DraftSessionListItemResponse]:
    """Return all past draft sessions for the current user."""
    statement = (
        select(DraftSessionModel)
        .where(DraftSessionModel.owner_id == current_user.username)
        .order_by(DraftSessionModel.updated_at.desc())
    )
    sessions = list(db.execute(statement).scalars().all())
    return [map_draft_session_list_item(session) for session in sessions]


@router.post("/{session_id}/generate", response_model=DraftSessionResponse, status_code=status.HTTP_202_ACCEPTED)
def generate_draft_session(
    session_id: str,
    response: Response,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PipelineOrchestratorService, Depends(get_pipeline_orchestrator_service)],
    dispatcher: Annotated[JobDispatcherService, Depends(get_job_dispatcher_service)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> DraftSessionResponse:
    """Queue background generation for process steps, notes, and screenshots."""
    session = service.mark_session_processing(db, session_id, owner_id=current_user.username)
    task_id = dispatcher.enqueue_draft_generation(session_id)
    response.headers["X-Task-Id"] = task_id
    return map_draft_session(session)


@router.get("/{session_id}", response_model=DraftSessionResponse)
def get_draft_session(
    session_id: str,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PipelineOrchestratorService, Depends(get_pipeline_orchestrator_service)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> DraftSessionResponse:
    """Return the structured draft session for review."""
    session = service.get_session(db, session_id, owner_id=current_user.username)
    return map_draft_session(session)


@router.patch("/{session_id}/steps/{step_id}", response_model=ProcessStepResponse)
def update_process_step(
    session_id: str,
    step_id: str,
    payload: ProcessStepUpdateRequest,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PipelineOrchestratorService, Depends(get_pipeline_orchestrator_service)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> ProcessStepResponse:
    """Persist a BA edit to a process step."""
    session = service.get_session(db, session_id, owner_id=current_user.username)
    step = next((item for item in session.process_steps if item.id == step_id), None)
    if step is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Process step not found.")

    updates = payload.model_dump(exclude_none=True)
    for field_name, field_value in updates.items():
        setattr(step, field_name, field_value)

    session.status = "review"
    db.add(step)
    db.commit()
    db.refresh(step)
    return map_process_step(step)


@router.patch("/{session_id}/steps/{step_id}/screenshots/{step_screenshot_id}", response_model=ProcessStepResponse)
def update_step_screenshot(
    session_id: str,
    step_id: str,
    step_screenshot_id: str,
    payload: StepScreenshotUpdateRequest,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PipelineOrchestratorService, Depends(get_pipeline_orchestrator_service)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> ProcessStepResponse:
    """Update ordering metadata for one step screenshot."""
    session = service.get_session(db, session_id, owner_id=current_user.username)
    step = next((item for item in session.process_steps if item.id == step_id), None)
    if step is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Process step not found.")

    step_screenshot = next((item for item in step.step_screenshots if item.id == step_screenshot_id), None)
    if step_screenshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Step screenshot not found.")

    updates = payload.model_dump(exclude_none=True)
    if updates.get("is_primary"):
        for item in step.step_screenshots:
            item.is_primary = item.id == step_screenshot.id
        step.screenshot_id = step_screenshot.artifact_id
    if "role" in updates:
        step_screenshot.role = updates["role"] or step_screenshot.role

    db.commit()
    db.refresh(step)
    return map_process_step(step)


@router.post(
    "/{session_id}/steps/{step_id}/candidate-screenshots/{candidate_screenshot_id}/select",
    response_model=ProcessStepResponse,
)
def select_candidate_screenshot(
    session_id: str,
    step_id: str,
    candidate_screenshot_id: str,
    payload: CandidateScreenshotSelectRequest,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PipelineOrchestratorService, Depends(get_pipeline_orchestrator_service)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> ProcessStepResponse:
    """Promote one generated candidate screenshot into the selected step evidence set."""
    session = service.get_session(db, session_id, owner_id=current_user.username)
    step = next((item for item in session.process_steps if item.id == step_id), None)
    if step is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Process step not found.")

    candidate = next((item for item in step.step_screenshot_candidates if item.id == candidate_screenshot_id), None)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate screenshot not found.")

    existing = next((item for item in step.step_screenshots if item.artifact_id == candidate.artifact_id), None)
    if existing is None:
        next_sequence = max((item.sequence_number for item in step.step_screenshots), default=0) + 1
        existing = ProcessStepScreenshotModel(
            step_id=step.id,
            artifact_id=candidate.artifact_id,
            role=payload.role or candidate.source_role or "during",
            sequence_number=next_sequence,
            timestamp=candidate.timestamp,
            selection_method="manual-candidate",
            is_primary=bool(payload.is_primary) or not step.step_screenshots,
        )
        db.add(existing)
        db.flush()
    elif payload.role:
        existing.role = payload.role

    if payload.is_primary or not any(item.is_primary for item in step.step_screenshots):
        for item in step.step_screenshots:
            item.is_primary = item.id == existing.id
        step.screenshot_id = existing.artifact_id
    elif not step.screenshot_id:
        step.screenshot_id = existing.artifact_id

    db.commit()
    db.refresh(step)
    return map_process_step(step)


@router.delete("/{session_id}/steps/{step_id}/screenshots/{step_screenshot_id}", response_model=ProcessStepResponse)
def delete_step_screenshot(
    session_id: str,
    step_id: str,
    step_screenshot_id: str,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PipelineOrchestratorService, Depends(get_pipeline_orchestrator_service)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> ProcessStepResponse:
    """Remove one screenshot from a step and promote the next one if needed."""
    session = service.get_session(db, session_id, owner_id=current_user.username)
    step = next((item for item in session.process_steps if item.id == step_id), None)
    if step is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Process step not found.")

    step_screenshot = next((item for item in step.step_screenshots if item.id == step_screenshot_id), None)
    if step_screenshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Step screenshot not found.")

    removed_artifact_id = step_screenshot.artifact_id
    db.delete(step_screenshot)
    db.flush()

    remaining = sorted(step.step_screenshots, key=lambda item: item.sequence_number)
    if remaining:
        has_primary = any(item.is_primary for item in remaining)
        if not has_primary:
            remaining[0].is_primary = True
        primary = next((item for item in remaining if item.is_primary), remaining[0])
        step.screenshot_id = primary.artifact_id
    else:
        step.screenshot_id = ""

    artifact_reference_count = db.query(ProcessStepScreenshotModel).filter(
        ProcessStepScreenshotModel.artifact_id == removed_artifact_id
    ).count()
    candidate_reference_count = db.query(ProcessStepScreenshotCandidateModel).filter(
        ProcessStepScreenshotCandidateModel.artifact_id == removed_artifact_id
    ).count()
    if artifact_reference_count == 0 and candidate_reference_count == 0:
        artifact = db.get(ArtifactModel, removed_artifact_id)
        if artifact is not None:
            db.delete(artifact)

    db.commit()
    db.refresh(step)
    return map_process_step(step)
