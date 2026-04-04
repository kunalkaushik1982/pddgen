from __future__ import annotations

from app.models.process_step import ProcessStepModel
from app.models.process_step_screenshot import ProcessStepScreenshotModel
from app.models.process_step_screenshot_candidate import ProcessStepScreenshotCandidateModel
from worker.pipeline.stages.persistence_records import attach_screenshot_evidence
from worker.pipeline.types import StepRecord


def persist_step_screenshots(db, *, step_models: list[ProcessStepModel], step_candidates: list[StepRecord]) -> None:  # type: ignore[no-untyped-def]
    relations: list[ProcessStepScreenshotModel] = []
    candidate_relations: list[ProcessStepScreenshotCandidateModel] = []
    for step_model, step_candidate in zip(step_models, step_candidates):
        attach_screenshot_evidence(step_candidate)
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
