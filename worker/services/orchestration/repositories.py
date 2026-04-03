from __future__ import annotations

from worker import bootstrap as _bootstrap  # noqa: F401
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.artifact import ArtifactModel
from app.models.draft_session import DraftSessionModel


class SqlAlchemyDraftSessionRepository:
    def load_draft_session(self, db, session_id: str) -> DraftSessionModel:  # type: ignore[no-untyped-def]
        statement = (
            select(DraftSessionModel)
            .where(DraftSessionModel.id == session_id)
            .options(
                selectinload(DraftSessionModel.artifacts).selectinload(ArtifactModel.meeting),
                selectinload(DraftSessionModel.process_steps),
                selectinload(DraftSessionModel.process_notes),
            )
        )
        session = db.execute(statement).scalar_one_or_none()
        if session is None:
            raise ValueError(f"Draft session '{session_id}' was not found.")
        return session
