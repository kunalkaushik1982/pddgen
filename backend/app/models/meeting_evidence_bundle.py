r"""
Purpose: Persist one paired transcript/video upload bundle within a meeting.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\models\meeting_evidence_bundle.py
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.draft_session import DraftSessionModel
    from app.models.meeting import MeetingModel


class MeetingEvidenceBundleModel(Base):
    """Persist a stable transcript/video pairing unit created from one upload action."""

    __tablename__ = "meeting_evidence_bundles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(ForeignKey("draft_sessions.id", ondelete="CASCADE"), index=True)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"), index=True)
    upload_batch_id: Mapped[str] = mapped_column(String(36), index=True)
    pair_index: Mapped[int] = mapped_column(Integer, default=0)
    transcript_artifact_id: Mapped[str | None] = mapped_column(
        ForeignKey("artifacts.id", ondelete="SET NULL"),
        nullable=True,
    )
    video_artifact_id: Mapped[str | None] = mapped_column(
        ForeignKey("artifacts.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    session: Mapped["DraftSessionModel"] = relationship(back_populates="meeting_evidence_bundles")
    meeting: Mapped["MeetingModel"] = relationship(back_populates="evidence_bundles")
