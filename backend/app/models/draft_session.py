r"""
Purpose: SQLAlchemy model for one PDD generation workflow session.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\models\draft_session.py
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.artifact import ArtifactModel
    from app.models.output_document import OutputDocumentModel
    from app.models.process_note import ProcessNoteModel
    from app.models.process_step import ProcessStepModel


class DraftSessionModel(Base):
    """Persist one draft PDD session."""

    __tablename__ = "draft_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(255), default="Untitled PDD Session")
    owner_id: Mapped[str] = mapped_column(String(255), default="pilot-user")
    status: Mapped[str] = mapped_column(String(50), default="draft", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    artifacts: Mapped[list["ArtifactModel"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    process_steps: Mapped[list["ProcessStepModel"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    process_notes: Mapped[list["ProcessNoteModel"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    output_documents: Mapped[list["OutputDocumentModel"]] = relationship(back_populates="session", cascade="all, delete-orphan")
