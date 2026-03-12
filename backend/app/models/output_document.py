r"""
Purpose: SQLAlchemy model for generated DOCX outputs.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\models\output_document.py
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.draft_session import DraftSessionModel


class OutputDocumentModel(Base):
    """Persist one generated document for a draft session."""

    __tablename__ = "output_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(ForeignKey("draft_sessions.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20), default="docx")
    storage_path: Mapped[str] = mapped_column(Text())
    exported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    session: Mapped["DraftSessionModel"] = relationship(back_populates="output_documents")
