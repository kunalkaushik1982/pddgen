r"""
Purpose: SQLAlchemy model for one recorded meeting within a draft session.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\models\meeting.py
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.artifact import ArtifactModel
    from app.models.draft_session import DraftSessionModel
    from app.models.meeting_evidence_bundle import MeetingEvidenceBundleModel
    from app.models.process_note import ProcessNoteModel
    from app.models.process_step import ProcessStepModel


class MeetingModel(Base):
    """Persist one meeting used as input evidence for a session."""

    __tablename__ = "meetings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(ForeignKey("draft_sessions.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255), default="Meeting")
    meeting_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    order_index: Mapped[int | None] = mapped_column(Integer, nullable=True)

    session: Mapped["DraftSessionModel"] = relationship(back_populates="meetings")
    artifacts: Mapped[list["ArtifactModel"]] = relationship(back_populates="meeting")
    evidence_bundles: Mapped[list["MeetingEvidenceBundleModel"]] = relationship(back_populates="meeting")
    process_steps: Mapped[list["ProcessStepModel"]] = relationship(back_populates="meeting")
    process_notes: Mapped[list["ProcessNoteModel"]] = relationship(back_populates="meeting")
