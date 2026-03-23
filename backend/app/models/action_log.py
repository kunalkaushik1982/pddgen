r"""
Purpose: SQLAlchemy model for meaningful session activity events.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\models\action_log.py
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.draft_session import DraftSessionModel


class ActionLogModel(Base):
    """Persist one meaningful action against a draft session."""

    __tablename__ = "action_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(ForeignKey("draft_sessions.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(100), default="session_event")
    title: Mapped[str] = mapped_column(String(255))
    detail: Mapped[str] = mapped_column(Text(), default="")
    metadata_json: Mapped[str] = mapped_column(Text(), default="")
    actor: Mapped[str] = mapped_column(String(255), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    session: Mapped["DraftSessionModel"] = relationship(back_populates="action_logs")
