r"""
Purpose: Service for validating and storing uploaded artifacts.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\artifact_ingestion.py
"""

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.models.artifact import ArtifactModel
from app.models.draft_session import DraftSessionModel
from app.storage.storage_service import StorageService


class ArtifactIngestionService:
    """Coordinate draft session creation and artifact intake."""

    def __init__(self, storage_service: StorageService | None = None) -> None:
        self.storage_service = storage_service or StorageService()

    def create_session(self, db: Session, *, title: str, owner_id: str) -> DraftSessionModel:
        """Create and persist a new draft session."""
        session = DraftSessionModel(title=title, owner_id=owner_id)
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    def ingest_artifact(
        self,
        db: Session,
        *,
        session_id: str,
        upload: UploadFile,
        artifact_kind: str,
    ) -> ArtifactModel:
        """Validate, persist, and register a newly uploaded artifact."""
        session = db.get(DraftSessionModel, session_id)
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft session not found.")

        storage_path, size_bytes = self.storage_service.save_upload(
            session_id=session_id,
            upload=upload,
            artifact_kind=artifact_kind,
        )

        artifact = ArtifactModel(
            session_id=session_id,
            name=upload.filename or "artifact",
            kind=artifact_kind,
            storage_path=storage_path,
            content_type=upload.content_type,
            size_bytes=size_bytes,
        )
        db.add(artifact)
        db.commit()
        db.refresh(artifact)
        return artifact
