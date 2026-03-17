r"""
Purpose: API routes for draft session retrieval and BA review actions.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\api\routes\draft_sessions.py
"""

import json
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import (
    get_artifact_ingestion_service,
    get_current_user,
    get_session_chat_service,
    get_job_dispatcher_service,
    get_pipeline_orchestrator_service,
)
from app.db.session import get_db_session
from app.models.draft_session import DraftSessionModel
from app.models.user import UserModel
from app.schemas.draft_session import (
    DiagramModelResponse,
    DraftSessionListItemResponse,
    DraftSessionResponse,
    ProcessStepResponse,
    SessionAnswerResponse,
    SessionQuestionRequest,
)
from app.schemas.draft_session import SaveDiagramArtifactRequest, SaveDiagramModelRequest
from app.schemas.process_step import CandidateScreenshotSelectRequest, ProcessStepUpdateRequest, StepScreenshotUpdateRequest
from app.models.artifact import ArtifactModel
from app.models.diagram_layout import DiagramLayoutModel
from app.models.process_step_screenshot_candidate import ProcessStepScreenshotCandidateModel
from app.models.process_step_screenshot import ProcessStepScreenshotModel
from app.services.job_dispatcher import JobDispatcherService
from app.services.mappers import map_draft_session, map_draft_session_list_item, map_process_step
from app.services.action_log_service import ActionLogService
from app.services.process_diagram_service import ProcessDiagramService
from app.services.pipeline_orchestrator import PipelineOrchestratorService
from app.services.session_chat_service import SessionChatService
from app.services.artifact_ingestion import ArtifactIngestionService
from app.schemas.draft_session import DiagramLayoutResponse, SaveDiagramLayoutRequest

router = APIRouter(prefix="/draft-sessions", tags=["draft-sessions"])
diagram_service = ProcessDiagramService()
action_log_service = ActionLogService()


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
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> DraftSessionResponse:
    """Queue background generation for process steps, notes, and screenshots."""
    session = service.mark_session_processing(db, session_id, owner_id=current_user.username)
    action_log_service.record(
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
        answer = chat_service.ask(session=session, question=payload.question)
    except RuntimeError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    return SessionAnswerResponse.model_validate(answer)


@router.get("/{session_id}/diagram-model", response_model=DiagramModelResponse)
def get_diagram_model(
    session_id: str,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PipelineOrchestratorService, Depends(get_pipeline_orchestrator_service)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
    view: Literal["overview", "detailed"] = "overview",
) -> DiagramModelResponse:
    """Return a frontend-friendly diagram model for preview rendering."""
    session = service.get_session(db, session_id, owner_id=current_user.username)
    return DiagramModelResponse.model_validate(diagram_service.build_diagram_model(session, view))


@router.put("/{session_id}/diagram-model", response_model=DiagramModelResponse)
def save_diagram_model(
    session_id: str,
    payload: SaveDiagramModelRequest,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PipelineOrchestratorService, Depends(get_pipeline_orchestrator_service)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
    view: Literal["overview", "detailed"] = "detailed",
) -> DiagramModelResponse:
    """Persist an edited diagram graph for the requested view."""
    session = service.get_session(db, session_id, owner_id=current_user.username)
    model_payload = {
        "diagram_type": "flowchart",
        "view_type": view,
        "title": payload.title,
        "nodes": [node.model_dump() for node in payload.nodes],
        "edges": [edge.model_dump() for edge in payload.edges],
    }
    if view == "detailed":
        session.detailed_diagram_json = json.dumps(model_payload)
    else:
        session.overview_diagram_json = json.dumps(model_payload)
    db.add(session)
    db.commit()
    db.refresh(session)
    return DiagramModelResponse.model_validate(model_payload)


@router.get("/{session_id}/diagram-layout", response_model=DiagramLayoutResponse)
def get_diagram_layout(
    session_id: str,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PipelineOrchestratorService, Depends(get_pipeline_orchestrator_service)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
    view: Literal["overview", "detailed"] = "detailed",
) -> DiagramLayoutResponse:
    """Return the saved node positions for a session diagram view if available."""
    service.get_session(db, session_id, owner_id=current_user.username)
    layout = (
        db.query(DiagramLayoutModel)
        .filter(DiagramLayoutModel.session_id == session_id, DiagramLayoutModel.view_type == view)
        .one_or_none()
    )
    nodes: list[dict] = []
    export_preset = "balanced"
    canvas_settings = {"theme": "dark", "show_grid": True, "grid_density": "medium"}
    if layout is not None and layout.layout_json:
        try:
            parsed = json.loads(layout.layout_json)
            if isinstance(parsed, dict):
                nodes = parsed.get("nodes", [])
                export_preset = parsed.get("export_preset", "balanced") or "balanced"
                parsed_canvas_settings = parsed.get("canvas_settings", {})
                if isinstance(parsed_canvas_settings, dict):
                    canvas_settings = {
                        "theme": parsed_canvas_settings.get("theme", "dark") or "dark",
                        "show_grid": bool(parsed_canvas_settings.get("show_grid", True)),
                        "grid_density": parsed_canvas_settings.get("grid_density", "medium") or "medium",
                    }
            elif isinstance(parsed, list):
                nodes = parsed
        except json.JSONDecodeError:
            nodes = []
    return DiagramLayoutResponse(
        session_id=session_id,
        view_type=view,
        nodes=nodes,
        export_preset=export_preset,
        canvas_settings=canvas_settings,
    )


@router.put("/{session_id}/diagram-layout", response_model=DiagramLayoutResponse)
def save_diagram_layout(
    session_id: str,
    payload: SaveDiagramLayoutRequest,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[PipelineOrchestratorService, Depends(get_pipeline_orchestrator_service)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
    view: Literal["overview", "detailed"] = "detailed",
) -> DiagramLayoutResponse:
    """Persist draggable node positions for one diagram view."""
    service.get_session(db, session_id, owner_id=current_user.username)
    layout = (
        db.query(DiagramLayoutModel)
        .filter(DiagramLayoutModel.session_id == session_id, DiagramLayoutModel.view_type == view)
        .one_or_none()
    )
    if layout is None:
        layout = DiagramLayoutModel(session_id=session_id, view_type=view)
        db.add(layout)

    previous_canvas_settings = {"theme": "dark", "show_grid": True, "grid_density": "medium"}
    if layout.layout_json:
        try:
            previous_payload = json.loads(layout.layout_json)
            if isinstance(previous_payload, dict):
                parsed_previous_canvas = previous_payload.get("canvas_settings", {})
                if isinstance(parsed_previous_canvas, dict):
                    previous_canvas_settings = {
                        "theme": parsed_previous_canvas.get("theme", "dark") or "dark",
                        "show_grid": bool(parsed_previous_canvas.get("show_grid", True)),
                        "grid_density": parsed_previous_canvas.get("grid_density", "medium") or "medium",
                    }
        except json.JSONDecodeError:
            previous_canvas_settings = {"theme": "dark", "show_grid": True, "grid_density": "medium"}

    next_canvas_settings = payload.canvas_settings.model_dump()
    layout.layout_json = json.dumps(
        {
            "nodes": [node.model_dump() for node in payload.nodes],
            "export_preset": payload.export_preset,
            "canvas_settings": next_canvas_settings,
        }
    )
    theme_changed = previous_canvas_settings.get("theme") != next_canvas_settings.get("theme")
    grid_changed = previous_canvas_settings.get("show_grid") != next_canvas_settings.get("show_grid")
    if theme_changed or grid_changed:
        appearance_parts: list[str] = []
        if theme_changed:
            appearance_parts.append(f"theme {next_canvas_settings.get('theme', 'dark')}")
        if grid_changed:
            appearance_parts.append(f"grid {'on' if next_canvas_settings.get('show_grid', True) else 'off'}")
        action_title = "Diagram appearance updated"
        action_detail = f"{view.capitalize()} diagram saved with " + ", ".join(appearance_parts) + "."
    else:
        action_title = "Diagram saved"
        action_detail = f"{view.capitalize()} layout saved with {len(payload.nodes)} positioned nodes."
    action_log_service.record(
        db,
        session_id=session_id,
        event_type="diagram_saved",
        title=action_title,
        detail=action_detail,
        actor=current_user.username,
    )
    db.commit()
    db.refresh(layout)
    parsed = json.loads(layout.layout_json) if layout.layout_json else {"nodes": [], "export_preset": "balanced"}
    return DiagramLayoutResponse(
        session_id=session_id,
        view_type=view,
        nodes=parsed.get("nodes", []),
        export_preset=parsed.get("export_preset", "balanced") or "balanced",
        canvas_settings=parsed.get("canvas_settings", {"theme": "dark", "show_grid": True, "grid_density": "medium"}),
    )


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
    action_log_service.record(
        db,
        session_id=session_id,
        event_type="step_edited",
        title=f"Step {step.step_number} edited",
        detail=step.action_text,
        actor=current_user.username,
    )
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

    action_log_service.record(
        db,
        session_id=session_id,
        event_type="screenshot_updated",
        title=f"Step {step.step_number} screenshot updated",
        detail=step_screenshot.timestamp or step_screenshot.artifact.name,
        actor=current_user.username,
    )
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

    action_log_service.record(
        db,
        session_id=session_id,
        event_type="candidate_screenshot_selected",
        title=f"Candidate screenshot selected for step {step.step_number}",
        detail=candidate.artifact.name,
        actor=current_user.username,
    )
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

    action_log_service.record(
        db,
        session_id=session_id,
        event_type="screenshot_removed",
        title=f"Screenshot removed from step {step.step_number}",
        detail=removed_artifact_id,
        actor=current_user.username,
    )
    db.commit()
    db.refresh(step)
    return map_process_step(step)
