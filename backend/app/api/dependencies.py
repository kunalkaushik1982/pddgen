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
from app.services.artifact_ingestion import ArtifactIngestionService
from app.services.artifact_validation import ArtifactValidationService
from app.services.auth_service import AuthService
from app.services.auth_provider_registry import AuthProviderRegistry
from app.services.database_session_service import DatabaseSessionService
from app.services.draft_session_diagram_service import DraftSessionDiagramService
from app.services.draft_session_review_service import DraftSessionReviewService
from app.services.document_renderer import DocumentRendererService
from app.services.job_dispatcher import JobDispatcherService
from app.services.pipeline_orchestrator import PipelineOrchestratorService
from app.services.session_chat_service import SessionChatService
from app.storage.storage_service import StorageService


def get_storage_service() -> StorageService:
    """Provide the configured storage service."""
    return StorageService()


def get_artifact_ingestion_service() -> ArtifactIngestionService:
    """Provide the artifact ingestion service."""
    return ArtifactIngestionService(
        storage_service=get_storage_service(),
        validation_service=ArtifactValidationService(),
    )


def get_pipeline_orchestrator_service() -> PipelineOrchestratorService:
    """Provide the pipeline orchestration service."""
    return PipelineOrchestratorService(storage_service=get_storage_service())


def get_document_renderer_service() -> DocumentRendererService:
    """Provide the DOCX rendering service."""
    return DocumentRendererService(storage_service=get_storage_service())


def get_draft_session_diagram_service() -> DraftSessionDiagramService:
    """Provide the draft-session diagram mutation service."""
    return DraftSessionDiagramService()


def get_draft_session_review_service() -> DraftSessionReviewService:
    """Provide the BA review mutation service."""
    return DraftSessionReviewService()


def get_session_chat_service() -> SessionChatService:
    """Provide the session-grounded Q&A service."""
    return SessionChatService(storage_service=get_storage_service())


def get_job_dispatcher_service() -> JobDispatcherService:
    """Provide the background job dispatcher service."""
    return JobDispatcherService()


def get_auth_service() -> AuthService:
    """Provide the configured auth facade."""
    settings = get_settings()
    identity_provider = AuthProviderRegistry().build(settings)
    session_service = DatabaseSessionService() if settings.auth_session_backend == "database_token" else None
    return AuthService(identity_provider=identity_provider, session_service=session_service)


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
