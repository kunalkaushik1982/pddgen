r"""
Purpose: SQLAlchemy model for uploaded source artifacts.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\models\artifact.py
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.draft_session import DraftSessionModel


class ArtifactModel(Base):
    """Persist one uploaded artifact for a draft session."""

    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(ForeignKey("draft_sessions.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(50), index=True)
    storage_path: Mapped[str] = mapped_column(Text())
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    session: Mapped["DraftSessionModel"] = relationship(back_populates="artifacts")
