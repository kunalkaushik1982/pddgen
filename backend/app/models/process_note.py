r"""
Purpose: SQLAlchemy model for business rules and process notes.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\models\process_note.py
"""

from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.draft_session import DraftSessionModel
    from app.models.meeting import MeetingModel
    from app.models.process_group import ProcessGroupModel


class ProcessNoteModel(Base):
    """Persist transcript-derived business rules and notes."""

    __tablename__ = "process_notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(ForeignKey("draft_sessions.id", ondelete="CASCADE"), index=True)
    process_group_id: Mapped[str | None] = mapped_column(
        ForeignKey("process_groups.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    meeting_id: Mapped[str | None] = mapped_column(
        ForeignKey("meetings.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    text: Mapped[str] = mapped_column(Text())
    related_step_ids: Mapped[str] = mapped_column(Text(), default="[]")
    evidence_reference_ids: Mapped[str] = mapped_column(Text(), default="[]")
    confidence: Mapped[str] = mapped_column(String(20), default="medium")
    inference_type: Mapped[str] = mapped_column(String(128), default="explicit")

    session: Mapped["DraftSessionModel"] = relationship(back_populates="process_notes")
    process_group: Mapped["ProcessGroupModel"] = relationship(back_populates="process_notes")
    meeting: Mapped["MeetingModel"] = relationship(back_populates="process_notes")
