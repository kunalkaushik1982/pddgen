r"""
Purpose: API routes for DOCX generation and export.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\api\routes\exports.py
"""

from typing import Annotated
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_document_renderer_service, get_pipeline_orchestrator_service
from app.db.session import get_db_session
from app.models.user import UserModel
from app.schemas.draft_session import OutputDocumentResponse
from app.services.action_log_service import ActionLogService
from app.services.document_renderer import DocumentRendererService
from app.services.pipeline_orchestrator import PipelineOrchestratorService

router = APIRouter(prefix="/exports", tags=["exports"])
action_log_service = ActionLogService()


@router.post("/{session_id}/docx", response_model=OutputDocumentResponse)
def export_docx(
    session_id: str,
    db: Annotated[Session, Depends(get_db_session)],
    pipeline_service: Annotated[PipelineOrchestratorService, Depends(get_pipeline_orchestrator_service)],
    renderer_service: Annotated[DocumentRendererService, Depends(get_document_renderer_service)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> OutputDocumentResponse:
    """Render the reviewed draft into a DOCX document."""
    session = pipeline_service.get_session(db, session_id, owner_id=current_user.username)
    output_document = renderer_service.render_docx(db, session)
    action_log_service.record(
        db,
        session_id=session_id,
        event_type="export_generated",
        title="DOCX export generated",
        detail=output_document.storage_path,
        actor=current_user.username,
    )
    db.commit()
    return OutputDocumentResponse.model_validate(output_document)


@router.post("/{session_id}/docx/download")
def export_docx_download(
    session_id: str,
    db: Annotated[Session, Depends(get_db_session)],
    pipeline_service: Annotated[PipelineOrchestratorService, Depends(get_pipeline_orchestrator_service)],
    renderer_service: Annotated[DocumentRendererService, Depends(get_document_renderer_service)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> FileResponse:
    """Render the reviewed draft and return the DOCX as a direct download."""
    session = pipeline_service.get_session(db, session_id, owner_id=current_user.username)
    output_document = renderer_service.render_docx(db, session)
    action_log_service.record(
        db,
        session_id=session_id,
        event_type="export_generated",
        title="DOCX export generated",
        detail=output_document.storage_path,
        actor=current_user.username,
    )
    db.commit()
    file_path = Path(output_document.storage_path)
    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=file_path.name,
    )


@router.post("/{session_id}/pdf/download")
def export_pdf_download(
    session_id: str,
    db: Annotated[Session, Depends(get_db_session)],
    pipeline_service: Annotated[PipelineOrchestratorService, Depends(get_pipeline_orchestrator_service)],
    renderer_service: Annotated[DocumentRendererService, Depends(get_document_renderer_service)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> FileResponse:
    """Render the reviewed draft and return the PDF as a direct download."""
    session = pipeline_service.get_session(db, session_id, owner_id=current_user.username)
    output_document = renderer_service.render_pdf(db, session)
    action_log_service.record(
        db,
        session_id=session_id,
        event_type="export_generated",
        title="PDF export generated",
        detail=output_document.storage_path,
        actor=current_user.username,
    )
    db.commit()
    file_path = Path(output_document.storage_path)
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=file_path.name,
    )
