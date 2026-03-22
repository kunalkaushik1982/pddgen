r"""
Purpose: SQLAlchemy model for persisted diagram node positions per session and view.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\models\diagram_layout.py
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.draft_session import DraftSessionModel


class DiagramLayoutModel(Base):
    """Persist a saved diagram layout for one session and one view type."""

    __tablename__ = "diagram_layouts"

    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(ForeignKey("draft_sessions.id", ondelete="CASCADE"), index=True)
    process_group_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    view_type: Mapped[str] = mapped_column(index=True)
    layout_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    session: Mapped["DraftSessionModel"] = relationship(back_populates="diagram_layouts")
