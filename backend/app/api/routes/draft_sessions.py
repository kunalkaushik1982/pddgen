r"""
Purpose: API routes for draft session retrieval and BA review actions.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\api\routes\draft_sessions.py
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import (
    get_action_log_service,
    get_artifact_ingestion_service,
    get_current_user,
    get_draft_session_diagram_service,
    get_draft_session_review_service,
    get_job_dispatcher_service,
    get_pipeline_orchestrator_service,
    get_process_diagram_service,
    get_session_chat_service,
)
from app.core.observability import bind_log_context, get_logger
from app.db.session import get_db_session
from app.models.draft_session import DraftSessionModel
from app.models.user import UserModel
from app.schemas.draft_session import (
    DiagramLayoutResponse,
    DiagramModelResponse,
    DraftSessionListItemResponse,
    DraftSessionResponse,
    ProcessStepResponse,
    SaveDiagramArtifactRequest,
    SaveDiagramLayoutRequest,
    SaveDiagramModelRequest,
    SessionAnswerResponse,
    SessionQuestionRequest,
)
from app.schemas.process_step import CandidateScreenshotSelectRequest, ProcessStepUpdateRequest, StepScreenshotUpdateRequest
from app.services.action_log_service import ActionLogService
from app.services.artifact_ingestion import ArtifactIngestionService
from app.services.draft_session_diagram_service import DraftSessionDiagramService
from app.services.draft_session_review_service import DraftSessionReviewService
from app.services.job_dispatcher import JobDispatcherService
from app.services.mappers import map_draft_session, map_draft_session_list_item, map_process_step
from app.services.pipeline_orchestrator import PipelineOrchestratorService
from app.services.process_diagram_service import ProcessDiagramService
from app.services.session_chat_service import SessionChatService

router = APIRouter(prefix="/draft-sessions", tags=["draft-sessions"])
logger = get_logger(__name__)


@router.get("", response_model=list[DraftSessionListItemResponse])
def list_draft_sessions(
    db: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> list[DraftSessionListItemResponse]:
    """Return all past draft sessions for the current user."""
    statement = (
        select(DraftSessionModel)
        .where(DraftSessionModel.owner_id == current_user.username)
        .options(
            selectinload(DraftSessionModel.artifacts),
            selectinload(DraftSessionModel.action_logs),
        )
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
    action_log: Annotated[ActionLogService, Depends(get_action_log_service)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> DraftSessionResponse:
    """Queue background generation for process steps, notes, and screenshots."""
    with bind_log_context(session_id=session_id):
        session = service.mark_session_processing(db, session_id, owner_id=current_user.username)
        action_log.record(
            db,
            session_id=session.id,
            event_type="generation_queued",
            title="Draft generation queued",
            detail="Transcript interpretation and screenshot derivation queued.",
            actor=current_user.username,
        )
        db.commit()
        session = service.get_session(db, session_id, owner_id=current_user.username)
        task_id = dispatcher.enqueue_draft_generation(session_id)
        logger.info(
            "Draft generation accepted",
            extra={"event": "draft_generation.accepted", "task_id": task_id},
        )
        response.headers["X-Task-Id"] = task_id
        return map_draft_session(session)


@router.post("/{session_id}/generate-screenshots", response_model=DraftSessionResponse, status_code=status.HTTP_202_ACCEPTED)
def generate_session_screenshots(
    session_id: str,
    response: Response,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PipelineOrchestratorService, Depends(get_pipeline_orchestrator_service)],
    dispatcher: Annotated[JobDispatcherService, Depends(get_job_dispatcher_service)],
    action_log: Annotated[ActionLogService, Depends(get_action_log_service)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> DraftSessionResponse:
    """Queue background screenshot generation for the current canonical draft steps."""
    with bind_log_context(session_id=session_id):
        session = service.get_session(db, session_id, owner_id=current_user.username)
        video_artifacts = [artifact for artifact in session.artifacts if artifact.kind == "video"]
        if not session.process_steps:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Generate the draft before requesting screenshots.",
            )
        if not video_artifacts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one video artifact is required before generating screenshots.",
            )
        if not dispatcher.acquire_screenshot_generation_lock(session_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Screenshot generation is already queued or running for this session.",
            )

        try:
            action_log.record(
                db,
                session_id=session.id,
                event_type="screenshot_generation_queued",
                title="Screenshot generation queued",
                detail="Video-based screenshot derivation queued for the current canonical steps.",
                actor=current_user.username,
            )
            db.commit()
            session = service.get_session(db, session_id, owner_id=current_user.username)
            task_id = dispatcher.enqueue_screenshot_generation(session_id)
            logger.info(
                "Screenshot generation accepted",
                extra={"event": "screenshot_generation.accepted", "task_id": task_id},
            )
            response.headers["X-Task-Id"] = task_id
            return map_draft_session(session)
        except Exception:
            dispatcher.release_screenshot_generation_lock(session_id)
            raise


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


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_draft_session(
    session_id: str,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PipelineOrchestratorService, Depends(get_pipeline_orchestrator_service)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> Response:
    """Delete one draft-only session from Workspace."""
    service.delete_draft_session(db, session_id, owner_id=current_user.username)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{session_id}/ask", response_model=SessionAnswerResponse)
def ask_session(
    session_id: str,
    payload: SessionQuestionRequest,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PipelineOrchestratorService, Depends(get_pipeline_orchestrator_service)],
    chat_service: Annotated[SessionChatService, Depends(get_session_chat_service)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> SessionAnswerResponse:
    """Answer a grounded question using this session's transcripts, steps, and notes."""
    session = service.get_session(db, session_id, owner_id=current_user.username)
    try:
        answer = chat_service.ask(session=session, question=payload.question, process_group_id=payload.process_group_id)
    except RuntimeError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    return SessionAnswerResponse.model_validate(answer)


@router.get("/{session_id}/diagram-model", response_model=DiagramModelResponse)
def get_diagram_model(
    session_id: str,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PipelineOrchestratorService, Depends(get_pipeline_orchestrator_service)],
    diagram_read: Annotated[ProcessDiagramService, Depends(get_process_diagram_service)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
    view: Literal["overview", "detailed"] = "overview",
    process_group_id: str | None = None,
) -> DiagramModelResponse:
    """Return a frontend-friendly diagram model for preview rendering."""
    session = service.get_session(db, session_id, owner_id=current_user.username)
    return DiagramModelResponse.model_validate(diagram_read.build_diagram_model(session, view, process_group_id=process_group_id))


@router.put("/{session_id}/diagram-model", response_model=DiagramModelResponse)
def save_diagram_model(
    session_id: str,
    payload: SaveDiagramModelRequest,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PipelineOrchestratorService, Depends(get_pipeline_orchestrator_service)],
    diagram_mutation_service: Annotated[DraftSessionDiagramService, Depends(get_draft_session_diagram_service)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
    view: Literal["overview", "detailed"] = "detailed",
    process_group_id: str | None = None,
) -> DiagramModelResponse:
    """Persist an edited diagram graph for the requested view."""
    session = service.get_session(db, session_id, owner_id=current_user.username)
    model_payload = diagram_mutation_service.save_diagram_model(
        db,
        session=session,
        payload=payload,
        view=view,
        process_group_id=process_group_id,
    )
    return DiagramModelResponse.model_validate(model_payload)


@router.get("/{session_id}/diagram-layout", response_model=DiagramLayoutResponse)
def get_diagram_layout(
    session_id: str,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PipelineOrchestratorService, Depends(get_pipeline_orchestrator_service)],
    diagram_mutation_service: Annotated[DraftSessionDiagramService, Depends(get_draft_session_diagram_service)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
    view: Literal["overview", "detailed"] = "detailed",
    process_group_id: str | None = None,
) -> DiagramLayoutResponse:
    """Return the saved node positions for a session diagram view if available."""
    service.get_session(db, session_id, owner_id=current_user.username)
    layout_payload = diagram_mutation_service.get_diagram_layout(
        db,
        session_id=session_id,
        view=view,
        process_group_id=process_group_id,
    )
    return DiagramLayoutResponse(**layout_payload)


@router.put("/{session_id}/diagram-layout", response_model=DiagramLayoutResponse)
def save_diagram_layout(
    session_id: str,
    payload: SaveDiagramLayoutRequest,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PipelineOrchestratorService, Depends(get_pipeline_orchestrator_service)],
    diagram_mutation_service: Annotated[DraftSessionDiagramService, Depends(get_draft_session_diagram_service)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
    view: Literal["overview", "detailed"] = "detailed",
    process_group_id: str | None = None,
) -> DiagramLayoutResponse:
    """Persist draggable node positions for one diagram view."""
    service.get_session(db, session_id, owner_id=current_user.username)
    layout_payload = diagram_mutation_service.save_diagram_layout(
        db,
        session_id=session_id,
        payload=payload,
        actor=current_user.username,
        view=view,
        process_group_id=process_group_id,
    )
    return DiagramLayoutResponse(**layout_payload)


@router.post("/{session_id}/diagram-artifact", response_model=DraftSessionResponse)
def save_diagram_artifact(
    session_id: str,
    payload: SaveDiagramArtifactRequest,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PipelineOrchestratorService, Depends(get_pipeline_orchestrator_service)],
    artifact_service: Annotated[ArtifactIngestionService, Depends(get_artifact_ingestion_service)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> DraftSessionResponse:
    """Persist the browser-rendered detailed diagram image for export."""
    artifact_service.save_diagram_artifact(
        db,
        session_id=session_id,
        image_data_url=payload.image_data_url,
        owner_id=current_user.username,
    )
    session = service.get_session(db, session_id, owner_id=current_user.username)
    return map_draft_session(session)


@router.patch("/{session_id}/steps/{step_id}", response_model=ProcessStepResponse)
def update_process_step(
    session_id: str,
    step_id: str,
    payload: ProcessStepUpdateRequest,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PipelineOrchestratorService, Depends(get_pipeline_orchestrator_service)],
    review_service: Annotated[DraftSessionReviewService, Depends(get_draft_session_review_service)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> ProcessStepResponse:
    """Persist a BA edit to a process step."""
    session = service.get_session(db, session_id, owner_id=current_user.username)
    step = review_service.update_process_step(
        db,
        session=session,
        step_id=step_id,
        payload=payload,
        actor=current_user.username,
    )
    return map_process_step(step)


@router.patch("/{session_id}/steps/{step_id}/screenshots/{step_screenshot_id}", response_model=ProcessStepResponse)
def update_step_screenshot(
    session_id: str,
    step_id: str,
    step_screenshot_id: str,
    payload: StepScreenshotUpdateRequest,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PipelineOrchestratorService, Depends(get_pipeline_orchestrator_service)],
    review_service: Annotated[DraftSessionReviewService, Depends(get_draft_session_review_service)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> ProcessStepResponse:
    """Update ordering metadata for one step screenshot."""
    session = service.get_session(db, session_id, owner_id=current_user.username)
    step = review_service.update_step_screenshot(
        db,
        session=session,
        step_id=step_id,
        step_screenshot_id=step_screenshot_id,
        payload=payload,
        actor=current_user.username,
    )
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
    review_service: Annotated[DraftSessionReviewService, Depends(get_draft_session_review_service)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> ProcessStepResponse:
    """Promote one generated candidate screenshot into the selected step evidence set."""
    session = service.get_session(db, session_id, owner_id=current_user.username)
    step = review_service.select_candidate_screenshot(
        db,
        session=session,
        step_id=step_id,
        candidate_screenshot_id=candidate_screenshot_id,
        payload=payload,
        actor=current_user.username,
    )
    return map_process_step(step)


@router.delete("/{session_id}/steps/{step_id}/screenshots/{step_screenshot_id}", response_model=ProcessStepResponse)
def delete_step_screenshot(
    session_id: str,
    step_id: str,
    step_screenshot_id: str,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PipelineOrchestratorService, Depends(get_pipeline_orchestrator_service)],
    review_service: Annotated[DraftSessionReviewService, Depends(get_draft_session_review_service)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> ProcessStepResponse:
    """Remove one screenshot from a step and promote the next one if needed."""
    session = service.get_session(db, session_id, owner_id=current_user.username)
    step = review_service.delete_step_screenshot(
        db,
        session=session,
        step_id=step_id,
        step_screenshot_id=step_screenshot_id,
        actor=current_user.username,
    )
    return map_process_step(step)
