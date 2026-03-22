r"""
Purpose: SQLAlchemy model for one logical process group inside a session.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\models\process_group.py
"""

from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.draft_session import DraftSessionModel
    from app.models.process_note import ProcessNoteModel
    from app.models.process_step import ProcessStepModel


class ProcessGroupModel(Base):
    """Persist one logical business process cluster within a draft session."""

    __tablename__ = "process_groups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(ForeignKey("draft_sessions.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255), default="Process 1")
    canonical_slug: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(50), default="active")
    display_order: Mapped[int] = mapped_column(Integer, default=1)
    summary_text: Mapped[str] = mapped_column(Text, default="")
    overview_diagram_json: Mapped[str] = mapped_column(Text, default="")
    detailed_diagram_json: Mapped[str] = mapped_column(Text, default="")

    session: Mapped["DraftSessionModel"] = relationship(back_populates="process_groups")
    process_steps: Mapped[list["ProcessStepModel"]] = relationship(back_populates="process_group")
    process_notes: Mapped[list["ProcessNoteModel"]] = relationship(back_populates="process_group")
