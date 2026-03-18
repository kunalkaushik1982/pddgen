r"""
Purpose: Background draft-generation coordinator for transcript normalization and screenshot derivation.
Full filepath: C:\Users\work\Documents\PddGenerator\worker\services\draft_generation_worker.py
"""

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from worker.bootstrap import get_db_session
from worker.services.draft_generation_stage_services import (
    DiagramAssemblyStage,
    FailureStage,
    PersistenceStage,
    ScreenshotDerivationStage,
    SessionPreparationStage,
    TranscriptInterpretationStage,
)

from app.models.draft_session import DraftSessionModel

class DraftGenerationWorker:
    """Run draft generation through isolated worker stages."""

    def __init__(self) -> None:
        self.session_preparation_stage = SessionPreparationStage()
        self.transcript_stage = TranscriptInterpretationStage()
        self.screenshot_stage = ScreenshotDerivationStage()
        self.diagram_stage = DiagramAssemblyStage()
        self.persistence_stage = PersistenceStage()
        self.failure_stage = FailureStage()

    def run(self, session_id: str) -> dict[str, int | str]:
        """Generate draft steps, notes, and derived screenshots for a session."""
        db = get_db_session()
        try:
            session = self._load_session(db, session_id)
            context = self.session_preparation_stage.load_and_prepare(db, session)
            self.transcript_stage.run(db, context)
            self.screenshot_stage.run(db, context)
            self.diagram_stage.run(db, context)
            return self.persistence_stage.run(db, context)
        except Exception as exc:
            self.failure_stage.mark_failed(db, session_id, str(exc))
            raise
        finally:
            db.close()

    def _load_session(self, db, session_id: str) -> DraftSessionModel:
        statement = (
            select(DraftSessionModel)
            .where(DraftSessionModel.id == session_id)
            .options(
                selectinload(DraftSessionModel.artifacts),
                selectinload(DraftSessionModel.process_steps),
                selectinload(DraftSessionModel.process_notes),
            )
        )
        session = db.execute(statement).scalar_one_or_none()
        if session is None:
            raise ValueError(f"Draft session '{session_id}' was not found.")
        return session
