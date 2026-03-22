r"""
Purpose: Service for validating and storing uploaded artifacts.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\artifact_ingestion.py
"""

import base64

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.models.artifact import ArtifactModel
from app.models.draft_session import DraftSessionModel
from app.models.meeting_evidence_bundle import MeetingEvidenceBundleModel
from app.storage.storage_service import StorageService
from app.services.artifact_validation import ArtifactValidationService


class ArtifactIngestionService:
    """Coordinate draft session creation and artifact intake."""

    def __init__(
        self,
        storage_service: StorageService | None = None,
        validation_service: ArtifactValidationService | None = None,
    ) -> None:
        self.storage_service = storage_service or StorageService()
        self.validation_service = validation_service or ArtifactValidationService()

    def create_session(self, db: Session, *, title: str, owner_id: str, diagram_type: str) -> DraftSessionModel:
        """Create and persist a new draft session."""
        session = DraftSessionModel(title=title, owner_id=owner_id, diagram_type=diagram_type)
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
        owner_id: str,
        meeting_id: str | None = None,
        upload_batch_id: str | None = None,
        upload_pair_index: int | None = None,
    ) -> ArtifactModel:
        """Validate, persist, and register a newly uploaded artifact."""
        session = db.get(DraftSessionModel, session_id)
        if session is None or session.owner_id != owner_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft session not found.")

        self.validation_service.validate_upload(upload=upload, artifact_kind=artifact_kind)
        storage_path, size_bytes = self.storage_service.save_upload(
            session_id=session_id,
            upload=upload,
            artifact_kind=artifact_kind,
        )

        artifact = ArtifactModel(
            session_id=session_id,
            meeting_id=meeting_id,
            upload_batch_id=upload_batch_id,
            upload_pair_index=upload_pair_index,
            name=upload.filename or "artifact",
            kind=artifact_kind,
            storage_path=storage_path,
            content_type=upload.content_type,
            size_bytes=size_bytes,
        )
        db.add(artifact)
        db.commit()
        db.refresh(artifact)
        if upload_batch_id and meeting_id is not None:
            self._upsert_evidence_bundle(
                db,
                session_id=session_id,
                meeting_id=meeting_id,
                artifact=artifact,
                upload_batch_id=upload_batch_id,
                upload_pair_index=upload_pair_index or 0,
            )
        return artifact

    @staticmethod
    def _upsert_evidence_bundle(
        db: Session,
        *,
        session_id: str,
        meeting_id: str,
        artifact: ArtifactModel,
        upload_batch_id: str,
        upload_pair_index: int,
    ) -> None:
        bundle = (
            db.query(MeetingEvidenceBundleModel)
            .filter(
                MeetingEvidenceBundleModel.session_id == session_id,
                MeetingEvidenceBundleModel.meeting_id == meeting_id,
                MeetingEvidenceBundleModel.upload_batch_id == upload_batch_id,
                MeetingEvidenceBundleModel.pair_index == upload_pair_index,
            )
            .one_or_none()
        )
        if bundle is None:
            bundle = MeetingEvidenceBundleModel(
                session_id=session_id,
                meeting_id=meeting_id,
                upload_batch_id=upload_batch_id,
                pair_index=upload_pair_index,
            )
            db.add(bundle)

        if artifact.kind == "transcript":
            bundle.transcript_artifact_id = artifact.id
        elif artifact.kind == "video":
            bundle.video_artifact_id = artifact.id

        db.commit()

    def save_diagram_artifact(
        self,
        db: Session,
        *,
        session_id: str,
        image_data_url: str,
        owner_id: str,
    ) -> ArtifactModel:
        """Persist a browser-rendered detailed diagram image for export reuse."""
        session = db.get(DraftSessionModel, session_id)
        if session is None or session.owner_id != owner_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft session not found.")

        prefix = "data:image/png;base64,"
        if not image_data_url.startswith(prefix):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Diagram image payload must be a PNG data URL.")

        try:
            content = base64.b64decode(image_data_url[len(prefix) :], validate=True)
        except Exception as error:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Diagram image payload is invalid: {error}") from error

        filename = "detailed-process-flow.png"
        storage_path = self.storage_service.save_bytes(
            session_id=session_id,
            folder="diagram",
            filename=filename,
            content=content,
        )

        artifact = (
            db.query(ArtifactModel)
            .filter(
                ArtifactModel.session_id == session_id,
                ArtifactModel.kind == "diagram",
                ArtifactModel.name == filename,
            )
            .one_or_none()
        )
        if artifact is None:
            artifact = ArtifactModel(
                session_id=session_id,
                name=filename,
                kind="diagram",
                storage_path=storage_path,
                content_type="image/png",
                size_bytes=len(content),
            )
            db.add(artifact)
        else:
            artifact.storage_path = storage_path
            artifact.content_type = "image/png"
            artifact.size_bytes = len(content)

        db.commit()
        db.refresh(artifact)
        return artifact
