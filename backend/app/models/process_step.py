r"""
Purpose: SQLAlchemy model for extracted or edited AS-IS process steps.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\models\process_step.py
"""

from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.draft_session import DraftSessionModel
    from app.models.process_step_screenshot_candidate import ProcessStepScreenshotCandidateModel
    from app.models.process_step_screenshot import ProcessStepScreenshotModel


class ProcessStepModel(Base):
    """Persist a structured process step for the AS-IS flow."""

    __tablename__ = "process_steps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(ForeignKey("draft_sessions.id", ondelete="CASCADE"), index=True)
    step_number: Mapped[int] = mapped_column(Integer, index=True)
    application_name: Mapped[str] = mapped_column(String(255), default="")
    action_text: Mapped[str] = mapped_column(Text())
    source_data_note: Mapped[str] = mapped_column(Text(), default="")
    timestamp: Mapped[str] = mapped_column(String(50), default="")
    start_timestamp: Mapped[str] = mapped_column(String(50), default="")
    end_timestamp: Mapped[str] = mapped_column(String(50), default="")
    supporting_transcript_text: Mapped[str] = mapped_column(Text(), default="")
    screenshot_id: Mapped[str] = mapped_column(String(36), default="")
    confidence: Mapped[str] = mapped_column(String(20), default="medium")
    evidence_references: Mapped[str] = mapped_column(Text(), default="[]")
    edited_by_ba: Mapped[bool] = mapped_column(Boolean, default=False)

    session: Mapped["DraftSessionModel"] = relationship(back_populates="process_steps")
    step_screenshots: Mapped[list["ProcessStepScreenshotModel"]] = relationship(
        back_populates="step",
        cascade="all, delete-orphan",
        order_by="ProcessStepScreenshotModel.sequence_number",
    )
    step_screenshot_candidates: Mapped[list["ProcessStepScreenshotCandidateModel"]] = relationship(
        back_populates="step",
        cascade="all, delete-orphan",
        order_by="ProcessStepScreenshotCandidateModel.sequence_number",
    )
