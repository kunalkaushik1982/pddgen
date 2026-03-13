r"""
Purpose: Shared dependency providers for backend routes.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\api\dependencies.py
"""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.models.user import UserModel
from app.services.artifact_ingestion import ArtifactIngestionService
from app.services.auth_service import AuthService
from app.services.document_renderer import DocumentRendererService
from app.services.job_dispatcher import JobDispatcherService
from app.services.pipeline_orchestrator import PipelineOrchestratorService
from app.storage.storage_service import StorageService


def get_storage_service() -> StorageService:
    """Provide the configured storage service."""
    return StorageService()


def get_artifact_ingestion_service() -> ArtifactIngestionService:
    """Provide the artifact ingestion service."""
    return ArtifactIngestionService(storage_service=get_storage_service())


def get_pipeline_orchestrator_service() -> PipelineOrchestratorService:
    """Provide the pipeline orchestration service."""
    return PipelineOrchestratorService(storage_service=get_storage_service())


def get_document_renderer_service() -> DocumentRendererService:
    """Provide the DOCX rendering service."""
    return DocumentRendererService(storage_service=get_storage_service())


def get_job_dispatcher_service() -> JobDispatcherService:
    """Provide the background job dispatcher service."""
    return JobDispatcherService()


def get_auth_service() -> AuthService:
    """Provide the simple auth service."""
    return AuthService()


def get_current_user(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    db: Annotated[Session, Depends(get_db_session)] = None,
    auth_service: Annotated[AuthService, Depends(get_auth_service)] = None,
) -> UserModel:
    """Resolve the current authenticated user from the Bearer token."""
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    return auth_service.authenticate_token(db, token=token)
