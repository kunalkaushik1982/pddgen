from __future__ import annotations

from app.core.observability import bind_log_context, get_logger
from sqlalchemy import delete, select

from app.models.artifact import ArtifactModel
from app.models.process_group import ProcessGroupModel
from app.models.process_note import ProcessNoteModel
from app.models.process_step import ProcessStepModel
from app.models.process_step_screenshot import ProcessStepScreenshotModel
from app.models.process_step_screenshot_candidate import ProcessStepScreenshotCandidateModel
from worker.services.draft_generation.stage_context import DraftGenerationContext

logger = get_logger(__name__)


class SessionPreparationStage:
    """Load session inputs and clear stale generated entities."""

    def load_and_prepare(self, db, session) -> DraftGenerationContext:  # type: ignore[no-untyped-def]
        with bind_log_context(stage="session_preparation"):
            session.status = "processing"
            db.commit()

            transcript_artifacts = [artifact for artifact in session.artifacts if artifact.kind == "transcript"]
            video_artifacts = [artifact for artifact in session.artifacts if artifact.kind == "video"]
            if not transcript_artifacts:
                raise ValueError("No transcript artifacts found for draft generation.")

            step_ids_subquery = select(ProcessStepModel.id).where(ProcessStepModel.session_id == session.id)
            db.execute(delete(ProcessStepScreenshotModel).where(ProcessStepScreenshotModel.step_id.in_(step_ids_subquery)))
            db.execute(
                delete(ProcessStepScreenshotCandidateModel).where(
                    ProcessStepScreenshotCandidateModel.step_id.in_(step_ids_subquery)
                )
            )
            db.execute(delete(ProcessStepModel).where(ProcessStepModel.session_id == session.id))
            db.execute(delete(ProcessNoteModel).where(ProcessNoteModel.session_id == session.id))
            db.execute(delete(ProcessGroupModel).where(ProcessGroupModel.session_id == session.id))
            db.execute(delete(ArtifactModel).where(ArtifactModel.session_id == session.id, ArtifactModel.kind == "screenshot"))
            db.commit()
            logger.info(
                "Prepared session for generation",
                extra={
                    "event": "draft_generation.stage_completed",
                    "transcript_artifact_count": len(transcript_artifacts),
                    "video_artifact_count": len(video_artifacts),
                },
            )

            return DraftGenerationContext(
                session_id=session.id,
                session=session,
                document_type=getattr(session, "document_type", "pdd"),
                transcript_artifacts=transcript_artifacts,
                video_artifacts=video_artifacts,
            )
