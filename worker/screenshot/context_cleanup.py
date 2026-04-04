from __future__ import annotations

import json

from sqlalchemy import delete

from app.models.artifact import ArtifactModel
from app.models.process_step_screenshot import ProcessStepScreenshotModel
from app.models.process_step_screenshot_candidate import ProcessStepScreenshotCandidateModel


def reset_screenshot_state(db, *, session) -> None:  # type: ignore[no-untyped-def]
    step_ids = [step.id for step in session.process_steps]
    if step_ids:
        db.execute(delete(ProcessStepScreenshotModel).where(ProcessStepScreenshotModel.step_id.in_(step_ids)))
        db.execute(delete(ProcessStepScreenshotCandidateModel).where(ProcessStepScreenshotCandidateModel.step_id.in_(step_ids)))
    db.execute(delete(ArtifactModel).where(ArtifactModel.session_id == session.id, ArtifactModel.kind == "screenshot"))


def strip_screenshot_evidence(evidence_references_raw: str) -> list[dict]:
    try:
        parsed = json.loads(evidence_references_raw or "[]")
    except json.JSONDecodeError:
        parsed = []
    return [reference for reference in parsed if reference.get("kind") != "screenshot"]
