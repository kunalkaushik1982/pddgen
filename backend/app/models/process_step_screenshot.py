r"""
Purpose: SQLAlchemy model for ordered screenshot evidence attached to a process step.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\models\process_step_screenshot.py
"""

from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.artifact import ArtifactModel
    from app.models.process_step import ProcessStepModel


class ProcessStepScreenshotModel(Base):
    """Persist one ordered screenshot slot for a process step."""

    __tablename__ = "process_step_screenshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    step_id: Mapped[str] = mapped_column(ForeignKey("process_steps.id", ondelete="CASCADE"), index=True)
    artifact_id: Mapped[str] = mapped_column(ForeignKey("artifacts.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20), default="during")
    sequence_number: Mapped[int] = mapped_column(Integer, default=1)
    timestamp: Mapped[str] = mapped_column(String(50), default="")
    selection_method: Mapped[str] = mapped_column(String(50), default="span")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)

    step: Mapped["ProcessStepModel"] = relationship(back_populates="step_screenshots")
    artifact: Mapped["ArtifactModel"] = relationship()
