r"""
Purpose: API routes for artifact upload and intake.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\api\routes\uploads.py
"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_artifact_ingestion_service, get_current_user
from app.db.session import get_db_session
from app.models.user import UserModel
from app.schemas.common import ArtifactKind
from app.schemas.draft_session import ArtifactResponse, CreateDraftSessionRequest, DraftSessionResponse
from app.services.artifact_ingestion import ArtifactIngestionService
from app.services.action_log_service import ActionLogService
from app.services.mappers import map_draft_session
from app.models.artifact import ArtifactModel

router = APIRouter(prefix="/uploads", tags=["uploads"])
action_log_service = ActionLogService()


@router.post("/sessions", response_model=DraftSessionResponse, status_code=status.HTTP_201_CREATED)
def create_upload_session(
    payload: CreateDraftSessionRequest,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[ArtifactIngestionService, Depends(get_artifact_ingestion_service)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> DraftSessionResponse:
    """Create an upload session for required and optional artifacts."""
    session = service.create_session(
        db,
        title=payload.title,
        owner_id=current_user.username,
        diagram_type=payload.diagram_type,
    )
    action_log_service.record(
        db,
        session_id=session.id,
        event_type="session_created",
        title="Session created",
        detail=f"{session.title} ({session.diagram_type})",
        actor=current_user.username,
    )
    db.commit()
    db.refresh(session)
    return map_draft_session(session)


@router.post(
    "/sessions/{session_id}/artifacts",
    response_model=ArtifactResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_artifact(
    session_id: str,
    artifact_kind: Annotated[ArtifactKind, Form(...)],
    file: Annotated[UploadFile, File(...)],
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[ArtifactIngestionService, Depends(get_artifact_ingestion_service)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> ArtifactResponse:
    """Store one artifact for an existing draft session."""
    artifact = service.ingest_artifact(
        db,
        session_id=session_id,
        upload=file,
        artifact_kind=artifact_kind,
        owner_id=current_user.username,
    )
    action_log_service.record(
        db,
        session_id=session_id,
        event_type="artifact_uploaded",
        title=f"{artifact_kind} uploaded",
        detail=artifact.name,
        actor=current_user.username,
    )
    db.commit()
    db.refresh(artifact)
    return ArtifactResponse.model_validate(artifact)


@router.get("/artifacts/{artifact_id}/content")
def get_artifact_content(
    artifact_id: str,
    db: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> FileResponse:
    """Serve one stored artifact file for frontend preview."""
    artifact = db.get(ArtifactModel, artifact_id)
    if artifact is None or artifact.session.owner_id != current_user.username:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found.")
    return FileResponse(path=artifact.storage_path, media_type=artifact.content_type, filename=artifact.name)
