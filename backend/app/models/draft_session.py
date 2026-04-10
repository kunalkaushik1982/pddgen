r"""
Purpose: SQLAlchemy model for one PDD generation workflow session.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\models\draft_session.py
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.action_log import ActionLogModel
    from app.models.artifact import ArtifactModel
    from app.models.background_job_run import BackgroundJobRunModel
    from app.models.llm_usage_event import LlmUsageEventModel
    from app.models.diagram_layout import DiagramLayoutModel
    from app.models.meeting import MeetingModel
    from app.models.meeting_evidence_bundle import MeetingEvidenceBundleModel
    from app.models.output_document import OutputDocumentModel
    from app.models.process_group import ProcessGroupModel
    from app.models.process_note import ProcessNoteModel
    from app.models.process_step import ProcessStepModel


class DraftSessionModel(Base):
    """Persist one draft PDD session."""

    __tablename__ = "draft_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(255), default="Untitled PDD Session")
    owner_id: Mapped[str] = mapped_column(String(255), default="pilot-user")
    diagram_type: Mapped[str] = mapped_column(String(50), default="flowchart")
    document_type: Mapped[str] = mapped_column(String(50), default="pdd")
    overview_diagram_json: Mapped[str] = mapped_column(Text, default="")
    detailed_diagram_json: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(50), default="draft", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    draft_generation_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    draft_generation_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    screenshot_generation_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    screenshot_generation_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)

    artifacts: Mapped[list["ArtifactModel"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    meetings: Mapped[list["MeetingModel"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    meeting_evidence_bundles: Mapped[list["MeetingEvidenceBundleModel"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    process_groups: Mapped[list["ProcessGroupModel"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    action_logs: Mapped[list["ActionLogModel"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    diagram_layouts: Mapped[list["DiagramLayoutModel"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    process_steps: Mapped[list["ProcessStepModel"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    process_notes: Mapped[list["ProcessNoteModel"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    output_documents: Mapped[list["OutputDocumentModel"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    llm_usage_events: Mapped[list["LlmUsageEventModel"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    background_job_runs: Mapped[list["BackgroundJobRunModel"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
