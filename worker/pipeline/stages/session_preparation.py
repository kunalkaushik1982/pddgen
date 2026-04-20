from __future__ import annotations

import json

from app.core.config import get_settings
from app.core.observability import bind_log_context, get_logger
from sqlalchemy import delete, select

from app.models.action_log import ActionLogModel
from app.models.artifact import ArtifactModel
from app.models.process_group import ProcessGroupModel
from app.models.process_note import ProcessNoteModel
from app.models.process_step import ProcessStepModel
from app.models.process_step_screenshot import ProcessStepScreenshotModel
from app.models.process_step_screenshot_candidate import ProcessStepScreenshotCandidateModel
from worker.pipeline.stages.stage_context import DraftGenerationContext

logger = get_logger(__name__)


class SessionPreparationStage:
    """Load session inputs and clear stale generated entities."""

    def load_and_prepare(self, db, session) -> DraftGenerationContext:  # type: ignore[no-untyped-def]
        with bind_log_context(stage="session_preparation"):
            settings = get_settings()
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

            include_diagram = settings.ai_draft_generation_include_diagram_default
            latest_generation_queue_log = db.execute(
                select(ActionLogModel)
                .where(
                    ActionLogModel.session_id == session.id,
                    ActionLogModel.event_type == "generation_queued",
                )
                .order_by(ActionLogModel.created_at.desc())
            ).scalars().first()
            if latest_generation_queue_log and latest_generation_queue_log.metadata_json:
                try:
                    metadata = json.loads(latest_generation_queue_log.metadata_json)
                except json.JSONDecodeError:
                    metadata = {}
                if isinstance(metadata, dict) and isinstance(metadata.get("include_diagram"), bool):
                    include_diagram = metadata["include_diagram"]

            document_type = str(getattr(session, "document_type", "pdd") or "pdd").strip().lower()
            transcript_count = len(transcript_artifacts)
            brd_lean_mode = bool(settings.ai_brd_lean_mode_enabled and document_type == "brd")
            transcript_to_steps_max_steps = settings.ai_brd_transcript_to_steps_max_steps if brd_lean_mode else None
            capability_classification_enabled = True
            if brd_lean_mode and settings.ai_brd_run_capability_classification_only_for_multi_transcript:
                capability_classification_enabled = transcript_count > 1

            from worker.pipeline.stages.stage_context import SessionInputs
            return DraftGenerationContext(
                inputs=SessionInputs(
                    session_id=session.id,
                    session=session,
                    document_type=document_type,
                    include_diagram=include_diagram,
                    brd_lean_mode=brd_lean_mode,
                    transcript_to_steps_max_steps=transcript_to_steps_max_steps,
                    capability_classification_enabled=capability_classification_enabled,
                    transcript_artifacts=transcript_artifacts,
                    video_artifacts=video_artifacts,
                )
            )
