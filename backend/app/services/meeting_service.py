r"""
Purpose: Service for managing meetings and meeting ordering for draft sessions.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\meeting_service.py
"""

from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.artifact import ArtifactModel
from app.models.draft_session import DraftSessionModel
from app.models.meeting import MeetingModel
from app.models.meeting_evidence_bundle import MeetingEvidenceBundleModel
from app.storage.storage_service import StorageService


class MeetingService:
    """Manage session meeting metadata and stable ordering."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.storage_service = StorageService()

    def list_meetings(self, db: Session, *, session_id: str, owner_id: str) -> list[MeetingModel]:
        """Return meetings sorted by explicit order or timestamp fallback."""
        session = self._get_session(db, session_id=session_id, owner_id=owner_id)
        if not session.meetings:
            self.ensure_default_meeting(db, session=session, commit=True)
        statement = (
            select(MeetingModel)
            .where(MeetingModel.session_id == session_id)
            .order_by(MeetingModel.order_index.asc().nullslast(), MeetingModel.meeting_date.asc().nullslast(), MeetingModel.uploaded_at.asc())
        )
        return list(db.execute(statement).scalars().all())

    def create_meeting(
        self,
        db: Session,
        *,
        session_id: str,
        owner_id: str,
        title: str,
        meeting_date: datetime | None = None,
    ) -> MeetingModel:
        """Create a meeting with a default order index at the end."""
        session = self._get_session(db, session_id=session_id, owner_id=owner_id)
        existing = self.list_meetings(db, session_id=session_id, owner_id=owner_id)
        next_index = max((meeting.order_index or 0 for meeting in existing), default=0) + 1
        resolved_title = title.strip() if title.strip() else f"{self.settings.default_meeting_title_prefix} {next_index}"
        meeting = MeetingModel(
            session_id=session.id,
            title=resolved_title,
            meeting_date=meeting_date,
            uploaded_at=datetime.utcnow(),
            order_index=next_index,
        )
        db.add(meeting)
        db.commit()
        db.refresh(meeting)
        return meeting

    def update_meeting(
        self,
        db: Session,
        *,
        session_id: str,
        meeting_id: str,
        owner_id: str,
        title: str | None = None,
        meeting_date: datetime | None = None,
        set_meeting_date: bool = False,
        order_index: int | None = None,
        set_order_index: bool = False,
    ) -> MeetingModel:
        """Update meeting metadata."""
        session = self._get_session(db, session_id=session_id, owner_id=owner_id)
        meeting = db.get(MeetingModel, meeting_id)
        if meeting is None or meeting.session_id != session.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found.")
        if title is not None:
            meeting.title = title.strip()
        if set_meeting_date:
            meeting.meeting_date = meeting_date
        if set_order_index:
            meeting.order_index = order_index
        db.commit()
        db.refresh(meeting)
        return meeting

    def reorder_meetings(
        self,
        db: Session,
        *,
        session_id: str,
        owner_id: str,
        meeting_ids: list[str],
    ) -> list[MeetingModel]:
        """Set a stable sequential order for the provided meetings list."""
        session = self._get_session(db, session_id=session_id, owner_id=owner_id)
        meetings = self.list_meetings(db, session_id=session_id, owner_id=owner_id)
        meetings_by_id = {meeting.id: meeting for meeting in meetings}
        if any(meeting_id not in meetings_by_id for meeting_id in meeting_ids):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Meeting list included unknown ids.")
        for index, meeting_id in enumerate(meeting_ids, start=1):
            meetings_by_id[meeting_id].order_index = index
        db.commit()
        return self.list_meetings(db, session_id=session.id, owner_id=owner_id)

    def discard_pending_bundle(
        self,
        db: Session,
        *,
        session_id: str,
        bundle_id: str,
        owner_id: str,
    ) -> None:
        """Discard one uploaded-but-unprocessed evidence bundle and its artifacts."""
        session = self._get_session(db, session_id=session_id, owner_id=owner_id)
        bundle = db.get(MeetingEvidenceBundleModel, bundle_id)
        if bundle is None or bundle.session_id != session.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pending evidence bundle not found.",
            )
        if bundle.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only pending uploaded evidence can be discarded.",
            )
        if bundle.meeting_id is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This uploaded evidence is not linked to a discardable meeting.",
            )

        processed_meeting_ids = {step.meeting_id for step in session.process_steps if step.meeting_id}
        processed_meeting_ids.update(note.meeting_id for note in session.process_notes if note.meeting_id)
        if bundle.meeting_id in processed_meeting_ids:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This meeting has already been incorporated into the draft and cannot be discarded.",
            )

        processed_transcript_ids = {
            step.source_transcript_artifact_id for step in session.process_steps if step.source_transcript_artifact_id
        }
        if bundle.transcript_artifact_id is not None and bundle.transcript_artifact_id in processed_transcript_ids:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This uploaded evidence has already been incorporated into the draft and cannot be discarded.",
            )

        artifact_ids = [
            artifact_id
            for artifact_id in [bundle.transcript_artifact_id, bundle.video_artifact_id]
            if artifact_id is not None
        ]
        artifacts = db.execute(select(ArtifactModel).where(ArtifactModel.id.in_(artifact_ids))).scalars().all() if artifact_ids else []
        for artifact in artifacts:
            try:
                self.storage_service.delete(artifact.storage_path)
            except Exception:
                pass

        if artifact_ids:
            db.execute(delete(ArtifactModel).where(ArtifactModel.id.in_(artifact_ids)))
        db.delete(bundle)

        remaining_artifact_count = (
            db.execute(select(ArtifactModel).where(ArtifactModel.meeting_id == bundle.meeting_id))
            .scalars()
            .first()
        )
        if remaining_artifact_count is None:
            meeting = db.get(MeetingModel, bundle.meeting_id)
            if meeting is not None:
                db.delete(meeting)
        db.commit()

    def get_meeting_or_default(
        self,
        db: Session,
        *,
        session_id: str,
        owner_id: str,
        meeting_id: str | None,
    ) -> MeetingModel:
        """Resolve a meeting for upload; create default if needed."""
        session = self._get_session(db, session_id=session_id, owner_id=owner_id)
        if meeting_id:
            meeting = db.get(MeetingModel, meeting_id)
            if meeting is None or meeting.session_id != session.id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found.")
            return meeting
        return self.ensure_default_meeting(db, session=session)

    def ensure_default_meeting(self, db: Session, *, session: DraftSessionModel, commit: bool = True) -> MeetingModel:
        """Ensure the session has at least one meeting and return it."""
        meeting = (
            db.execute(select(MeetingModel).where(MeetingModel.session_id == session.id).order_by(MeetingModel.order_index.asc().nullslast()))
            .scalars()
            .first()
        )
        if meeting is not None:
            return meeting
        meeting = MeetingModel(
            session_id=session.id,
            title=f"{self.settings.default_meeting_title_prefix} 1",
            meeting_date=None,
            uploaded_at=datetime.utcnow(),
            order_index=1,
        )
        db.add(meeting)
        if commit:
            db.commit()
        else:
            db.flush()
        db.refresh(meeting)
        return meeting

    @staticmethod
    def _get_session(db: Session, *, session_id: str, owner_id: str) -> DraftSessionModel:
        session = db.get(DraftSessionModel, session_id)
        if session is None or session.owner_id != owner_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft session not found.")
        return session
