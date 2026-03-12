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


class ProcessNoteModel(Base):
    """Persist transcript-derived business rules and notes."""

    __tablename__ = "process_notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(ForeignKey("draft_sessions.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(Text())
    related_step_ids: Mapped[str] = mapped_column(Text(), default="[]")
    evidence_reference_ids: Mapped[str] = mapped_column(Text(), default="[]")
    confidence: Mapped[str] = mapped_column(String(20), default="medium")
    inference_type: Mapped[str] = mapped_column(String(20), default="explicit")

    session: Mapped["DraftSessionModel"] = relationship(back_populates="process_notes")
