from __future__ import annotations

from app.core.observability import bind_log_context, get_logger
from sqlalchemy import select

from app.models.action_log import ActionLogModel
from app.models.meeting_evidence_bundle import MeetingEvidenceBundleModel
from app.models.process_note import ProcessNoteModel
from app.models.process_step import ProcessStepModel
from worker.pipeline.stages.stage_context import DraftGenerationContext
from worker.pipeline.stages.persistence_records import to_note_record, to_step_record
from worker.pipeline.stages.persistence_screenshots import persist_step_screenshots
from worker.pipeline.types import NoteRecord, StepRecord

logger = get_logger(__name__)


class PersistenceStage:
    """Persist generated steps, notes, screenshots, and final status."""

    def run(self, db, context: DraftGenerationContext) -> dict[str, int | str]:  # type: ignore[no-untyped-def]
        with bind_log_context(stage="persistence"):
            selected_screenshot_count = sum(len(step.get("_derived_screenshots", [])) for step in context.all_steps)
            context.session.overview_diagram_json = context.overview_diagram_json
            context.session.detailed_diagram_json = context.detailed_diagram_json

            step_models = [ProcessStepModel(session_id=context.session_id, **to_step_record(step)) for step in context.all_steps]
            db.add_all(step_models)
            db.flush()
            persist_step_screenshots(db, step_models=step_models, step_candidates=context.all_steps)
            db.add_all(ProcessNoteModel(session_id=context.session_id, **to_note_record(note)) for note in context.all_notes)
            pending_bundles = (
                db.execute(
                    select(MeetingEvidenceBundleModel).where(
                        MeetingEvidenceBundleModel.session_id == context.session_id,
                        MeetingEvidenceBundleModel.status == "pending",
                    )
                )
                .scalars()
                .all()
            )
            for bundle in pending_bundles:
                bundle.status = "processed"
            context.session.status = "review"
            db.add(
                ActionLogModel(
                    session_id=context.session_id,
                    event_type="draft_generated",
                    title="Ready for review",
                    detail=(
                        f"{len(context.all_steps)} steps, "
                        f"{len(context.all_notes)} notes, "
                        f"{selected_screenshot_count} screenshots."
                    ),
                    actor="system",
                )
            )
            db.commit()
            result = {
                "session_id": context.session_id,
                "steps_created": len(context.all_steps),
                "notes_created": len(context.all_notes),
                "screenshots_created": selected_screenshot_count,
            }
            logger.info("Persistence stage completed", extra={"event": "draft_generation.stage_completed", **result})
            return result
