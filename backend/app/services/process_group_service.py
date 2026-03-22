r"""
Purpose: Service for default process-group management inside a draft session.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\process_group_service.py
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.draft_session import DraftSessionModel
from app.models.process_group import ProcessGroupModel


class ProcessGroupService:
    """Manage default process groups for sessions."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def ensure_default_process_group(self, db: Session, *, session: DraftSessionModel) -> ProcessGroupModel:
        """Ensure the session has at least one process group and return it."""
        process_group = (
            db.execute(
                select(ProcessGroupModel)
                .where(ProcessGroupModel.session_id == session.id)
                .order_by(ProcessGroupModel.display_order.asc(), ProcessGroupModel.id.asc())
            )
            .scalars()
            .first()
        )
        if process_group is not None:
            return process_group

        process_group = ProcessGroupModel(
            session_id=session.id,
            title=f"{self.settings.default_process_group_title_prefix} 1",
            canonical_slug="process-1",
            status="active",
            display_order=1,
        )
        db.add(process_group)
        db.commit()
        db.refresh(process_group)
        return process_group

    def reset_process_groups(self, db: Session, *, session: DraftSessionModel) -> None:
        """Delete all process groups for a session before a full regeneration rebuild."""
        db.execute(delete(ProcessGroupModel).where(ProcessGroupModel.session_id == session.id))
        db.commit()

    def create_process_group(
        self,
        db: Session,
        *,
        session: DraftSessionModel,
        title: str,
        canonical_slug: str,
        display_order: int,
    ) -> ProcessGroupModel:
        """Create a new process group for the session."""
        process_group = ProcessGroupModel(
            session_id=session.id,
            title=title.strip() or f"{self.settings.default_process_group_title_prefix} {display_order}",
            canonical_slug=canonical_slug.strip() or f"process-{display_order}",
            status="active",
            display_order=display_order,
        )
        db.add(process_group)
        db.commit()
        db.refresh(process_group)
        return process_group

    def list_process_groups(self, db: Session, *, session_id: str, owner_id: str) -> list[ProcessGroupModel]:
        """Return process groups for one session, ensuring a default group exists."""
        session = self._get_session(db, session_id=session_id, owner_id=owner_id)
        self.ensure_default_process_group(db, session=session)
        statement = (
            select(ProcessGroupModel)
            .where(ProcessGroupModel.session_id == session_id)
            .order_by(ProcessGroupModel.display_order.asc(), ProcessGroupModel.id.asc())
        )
        return list(db.execute(statement).scalars().all())

    @staticmethod
    def _get_session(db: Session, *, session_id: str, owner_id: str) -> DraftSessionModel:
        session = db.get(DraftSessionModel, session_id)
        if session is None or session.owner_id != owner_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft session not found.")
        return session
