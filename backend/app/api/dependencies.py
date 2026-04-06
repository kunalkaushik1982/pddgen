r"""
Purpose: Shared dependency providers for backend routes.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\api\dependencies.py
"""

from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.observability import set_log_context
from app.db.session import get_db_session
from app.models.user import UserModel
from app.services.action_log_service import ActionLogService
from app.services.artifact_ingestion import ArtifactIngestionService
from app.services.artifact_validation import ArtifactValidationService
from app.portability.auth_registry import build_identity_provider
from app.portability.http_client import build_llm_http_client
from app.services.auth_service import AuthService
from app.services.database_session_service import DatabaseSessionService
from app.services.draft_session_diagram_service import DraftSessionDiagramService
from app.services.draft_session_review_service import DraftSessionReviewService
from app.portability.celery_job_queue import build_default_job_queue
from app.services.document_pdf_converter import DocumentPdfConverter
from app.services.document_renderer import DocumentRendererService
from app.services.document_template_renderer import DocumentTemplateRenderer
from app.services.job_dispatcher import JobDispatcherService
from app.services.meeting_service import MeetingService
from app.services.pipeline_orchestrator import PipelineOrchestratorService
from app.services.process_diagram_service import ProcessDiagramService
from app.services.process_group_service import ProcessGroupService
from app.services.screenshot_mapping import ScreenshotMappingService
from app.services.session_chat_service import SessionChatService
from app.services.step_extraction import StepExtractionService
from app.services.transcript_intelligence import TranscriptIntelligenceService
from app.storage.storage_service import StorageService


def get_storage_service() -> StorageService:
    """Provide the configured storage service."""
    return StorageService()


def get_artifact_ingestion_service() -> ArtifactIngestionService:
    """Provide the artifact ingestion service."""
    settings = get_settings()
    return ArtifactIngestionService(
        storage_service=get_storage_service(),
        validation_service=ArtifactValidationService(settings=settings),
    )


def get_action_log_service() -> ActionLogService:
    """Provide the audit action-log service."""
    return ActionLogService()


def get_process_diagram_service() -> ProcessDiagramService:
    """Provide the read-model diagram builder for API responses."""
    return ProcessDiagramService()


def get_document_template_renderer_service() -> DocumentTemplateRenderer:
    """Provide the DOCX template renderer (registry wired with shared ProcessDiagramService)."""
    return DocumentTemplateRenderer(
        process_diagram_service=get_process_diagram_service(),
        context_builder=None,
    )


def get_pipeline_orchestrator_service() -> PipelineOrchestratorService:
    """Provide the pipeline orchestration service (fully wired from this composition root)."""
    storage = get_storage_service()
    return PipelineOrchestratorService(
        storage_service=storage,
        step_extraction_service=StepExtractionService(),
        transcript_intelligence_service=TranscriptIntelligenceService(),
        screenshot_mapping_service=ScreenshotMappingService(),
        process_group_service=get_process_group_service(),
    )


def get_document_renderer_service() -> DocumentRendererService:
    """Provide the DOCX/PDF rendering service."""
    storage = get_storage_service()
    return DocumentRendererService(
        storage_service=storage,
        template_renderer=get_document_template_renderer_service(),
        pdf_converter=DocumentPdfConverter(),
    )


def get_draft_session_diagram_service() -> DraftSessionDiagramService:
    """Provide the draft-session diagram mutation service."""
    return DraftSessionDiagramService(action_log_service=get_action_log_service())


def get_draft_session_review_service() -> DraftSessionReviewService:
    """Provide the BA review mutation service."""
    return DraftSessionReviewService(action_log_service=get_action_log_service())


def get_session_chat_service() -> SessionChatService:
    """Provide the session-grounded Q&A service."""
    settings = get_settings()
    llm_client = build_llm_http_client(settings) if settings.ai_enabled else None
    return SessionChatService(
        storage_service=get_storage_service(),
        llm_http_client=llm_client,
    )


def get_job_dispatcher_service() -> JobDispatcherService:
    """Provide the background job dispatcher service."""
    return JobDispatcherService(queue=build_default_job_queue(get_settings()))

def get_meeting_service() -> MeetingService:
    """Provide meeting management service."""
    return MeetingService()


def get_process_group_service() -> ProcessGroupService:
    """Provide process-group management service."""
    return ProcessGroupService()


def get_auth_service() -> AuthService:
    """Provide the configured auth facade."""
    settings = get_settings()
    return AuthService(
        identity_provider=build_identity_provider(settings),
        session_service=DatabaseSessionService(),
    )


def get_current_user(
    session_cookie: Annotated[str | None, Cookie(alias=get_settings().auth_cookie_name)] = None,
    db: Annotated[Session, Depends(get_db_session)] = None,
    auth_service: Annotated[AuthService, Depends(get_auth_service)] = None,
) -> UserModel:
    """Resolve the current authenticated user from the configured session transport."""
    if session_cookie:
        user = auth_service.authenticate_token(db, token=session_cookie)
        set_log_context(actor=user.username)
        return user
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")


def get_current_admin_user(
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> UserModel:
    """Resolve the current authenticated admin user."""
    settings = get_settings()
    if current_user.username not in settings.admin_usernames:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    return current_user
