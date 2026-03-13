r"""
Purpose: SQLAlchemy model for candidate screenshot evidence generated for a process step.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\models\process_step_screenshot_candidate.py
"""

from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.artifact import ArtifactModel
    from app.models.process_step import ProcessStepModel


class ProcessStepScreenshotCandidateModel(Base):
    """Persist one generated candidate screenshot for later BA selection."""

    __tablename__ = "process_step_screenshot_candidates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    step_id: Mapped[str] = mapped_column(ForeignKey("process_steps.id", ondelete="CASCADE"), index=True)
    artifact_id: Mapped[str] = mapped_column(ForeignKey("artifacts.id", ondelete="CASCADE"), index=True)
    sequence_number: Mapped[int] = mapped_column(Integer, default=1)
    timestamp: Mapped[str] = mapped_column(String(50), default="")
    source_role: Mapped[str] = mapped_column(String(20), default="candidate")
    selection_method: Mapped[str] = mapped_column(String(50), default="span-candidate")

    step: Mapped["ProcessStepModel"] = relationship(back_populates="step_screenshot_candidates")
    artifact: Mapped["ArtifactModel"] = relationship()
