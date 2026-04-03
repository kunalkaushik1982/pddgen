from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from worker import bootstrap as _bootstrap  # noqa: F401
from app.core.observability import bind_log_context, get_logger
from sqlalchemy import select

from app.models.action_log import ActionLogModel
from app.models.meeting_evidence_bundle import MeetingEvidenceBundleModel
from app.models.process_note import ProcessNoteModel
from app.models.process_step import ProcessStepModel
from app.models.process_step_screenshot import ProcessStepScreenshotModel
from app.models.process_step_screenshot_candidate import ProcessStepScreenshotCandidateModel
from worker.services.draft_generation.stage_context import DraftGenerationContext
from worker.services.generation_types import NoteRecord, StepRecord

logger = get_logger(__name__)


class PersistenceStage:
    """Persist generated steps, notes, screenshots, and final status."""

    def run(self, db: Any, context: DraftGenerationContext) -> dict[str, int | str]:
        with bind_log_context(stage="persistence"):
            selected_screenshot_count = sum(len(step.get("_derived_screenshots", [])) for step in context.all_steps)
            context.session.overview_diagram_json = context.overview_diagram_json
            context.session.detailed_diagram_json = context.detailed_diagram_json

            step_models = [ProcessStepModel(session_id=context.session_id, **self._to_step_record(step)) for step in context.all_steps]
            db.add_all(step_models)
            db.flush()
            self._persist_step_screenshots(db, step_models, context.all_steps)
            db.add_all(ProcessNoteModel(session_id=context.session_id, **self._to_note_record(note)) for note in context.all_notes)
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

    @staticmethod
    def _attach_screenshot_evidence(step: StepRecord) -> None:
        derived_screenshots = step.get("_derived_screenshots", [])
        if not derived_screenshots:
            return
        evidence_references = json.loads(step["evidence_references"])
        for screenshot in derived_screenshots:
            evidence_references.append(
                {
                    "id": str(uuid4()),
                    "artifact_id": screenshot["artifact"].id,
                    "kind": "screenshot",
                    "locator": screenshot["timestamp"] or step.get("timestamp") or f"step:{step['step_number']}",
                }
            )
        step["evidence_references"] = json.dumps(evidence_references)

    def _persist_step_screenshots(self, db: Any, step_models: list[ProcessStepModel], step_candidates: list[StepRecord]) -> None:
        relations: list[ProcessStepScreenshotModel] = []
        candidate_relations: list[ProcessStepScreenshotCandidateModel] = []
        for step_model, step_candidate in zip(step_models, step_candidates):
            self._attach_screenshot_evidence(step_candidate)
            step_model.evidence_references = step_candidate["evidence_references"]
            step_model.screenshot_id = step_candidate.get("screenshot_id", "")
            step_model.timestamp = step_candidate.get("timestamp", "")
            for candidate in step_candidate.get("_candidate_screenshots", []):
                candidate_relations.append(
                    ProcessStepScreenshotCandidateModel(
                        step_id=step_model.id,
                        artifact_id=candidate["artifact"].id,
                        sequence_number=candidate["sequence_number"],
                        timestamp=candidate["timestamp"],
                        source_role=candidate["source_role"],
                        selection_method=candidate["selection_method"],
                    )
                )
            for screenshot in step_candidate.get("_derived_screenshots", []):
                relations.append(
                    ProcessStepScreenshotModel(
                        step_id=step_model.id,
                        artifact_id=screenshot["artifact"].id,
                        role=screenshot["role"],
                        sequence_number=screenshot["sequence_number"],
                        timestamp=screenshot["timestamp"],
                        selection_method=screenshot["selection_method"],
                        is_primary=screenshot["is_primary"],
                    )
                )
        if candidate_relations:
            db.add_all(candidate_relations)
        if relations:
            db.add_all(relations)

    @staticmethod
    def _to_step_record(step: StepRecord) -> dict[str, object]:
        record = {
            key: value
            for key, value in step.items()
            if key not in {"_candidate_screenshots", "_derived_screenshots", "_transcript_artifact_id"}
        }
        record["source_transcript_artifact_id"] = step.get("_transcript_artifact_id")
        return record

    @staticmethod
    def _to_note_record(note: NoteRecord) -> dict[str, object]:
        return {key: value for key, value in note.items() if key != "_transcript_artifact_id"}
