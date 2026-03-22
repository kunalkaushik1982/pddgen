r"""
Purpose: Background draft-generation coordinator for transcript normalization and screenshot derivation.
Full filepath: C:\Users\work\Documents\PddGenerator\worker\services\draft_generation_worker.py
"""

from app.core.observability import bind_log_context, get_logger
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from worker.bootstrap import get_db_session
from worker.services.draft_generation_stage_services import (
    CanonicalMergeStage,
    DiagramAssemblyStage,
    FailureStage,
    PersistenceStage,
    ProcessGroupingStage,
    SessionPreparationStage,
    TranscriptInterpretationStage,
)

from app.models.artifact import ArtifactModel
from app.models.draft_session import DraftSessionModel

logger = get_logger(__name__)


class DraftGenerationWorker:
    """Run draft generation through isolated worker stages."""

    def __init__(self, task_id: str | None = None) -> None:
        self.task_id = task_id
        self.session_preparation_stage = SessionPreparationStage()
        self.transcript_stage = TranscriptInterpretationStage()
        self.process_grouping_stage = ProcessGroupingStage()
        self.canonical_merge_stage = CanonicalMergeStage()
        self.diagram_stage = DiagramAssemblyStage()
        self.persistence_stage = PersistenceStage()
        self.failure_stage = FailureStage()

    def run(self, session_id: str) -> dict[str, int | str]:
        """Generate draft steps, notes, and derived screenshots for a session."""
        db = get_db_session()
        try:
            with bind_log_context(task_id=self.task_id, session_id=session_id):
                session = self._load_session(db, session_id)
                logger.info("Loaded draft session for background generation", extra={"event": "draft_generation.session_loaded"})
                context = self.session_preparation_stage.load_and_prepare(db, session)
                self.transcript_stage.run(db, context)
                self.process_grouping_stage.run(db, context)
                self.canonical_merge_stage.run(db, context)
                self.diagram_stage.run(db, context)
                result = self.persistence_stage.run(db, context)
                logger.info(
                    "Persisted generated draft artifacts",
                    extra={"event": "draft_generation.persisted", **result},
                )
                return result
        except Exception as exc:
            logger.exception("Draft generation pipeline failed", extra={"event": "draft_generation.failed"})
            self.failure_stage.mark_failed(db, session_id, str(exc))
            raise
        finally:
            db.close()

    def _load_session(self, db, session_id: str) -> DraftSessionModel:
        statement = (
            select(DraftSessionModel)
            .where(DraftSessionModel.id == session_id)
            .options(
                selectinload(DraftSessionModel.artifacts).selectinload(ArtifactModel.meeting),
                selectinload(DraftSessionModel.process_steps),
                selectinload(DraftSessionModel.process_notes),
            )
        )
        session = db.execute(statement).scalar_one_or_none()
        if session is None:
            raise ValueError(f"Draft session '{session_id}' was not found.")
        return session
