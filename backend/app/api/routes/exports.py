r"""
Purpose: API routes for DOCX generation and export.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\api\routes\exports.py
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_document_renderer_service, get_pipeline_orchestrator_service
from app.db.session import get_db_session
from app.schemas.draft_session import OutputDocumentResponse
from app.services.document_renderer import DocumentRendererService
from app.services.pipeline_orchestrator import PipelineOrchestratorService

router = APIRouter(prefix="/exports", tags=["exports"])


@router.post("/{session_id}/docx", response_model=OutputDocumentResponse)
def export_docx(
    session_id: str,
    db: Annotated[Session, Depends(get_db_session)],
    pipeline_service: Annotated[PipelineOrchestratorService, Depends(get_pipeline_orchestrator_service)],
    renderer_service: Annotated[DocumentRendererService, Depends(get_document_renderer_service)],
) -> OutputDocumentResponse:
    """Render the reviewed draft into a DOCX document."""
    session = pipeline_service.get_session(db, session_id)
    output_document = renderer_service.render_docx(db, session)
    return OutputDocumentResponse.model_validate(output_document)
