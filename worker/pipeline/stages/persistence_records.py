from __future__ import annotations

import json
from uuid import uuid4

from worker.pipeline.types import NoteRecord, StepRecord


def attach_screenshot_evidence(step: StepRecord) -> None:
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


def to_step_record(step: StepRecord) -> dict[str, object]:
    record = {
        key: value
        for key, value in step.items()
        if key not in {"_candidate_screenshots", "_derived_screenshots", "_transcript_artifact_id"}
    }
    record["source_transcript_artifact_id"] = step.get("_transcript_artifact_id")
    return record


def to_note_record(note: NoteRecord) -> dict[str, object]:
    return {key: value for key, value in note.items() if key != "_transcript_artifact_id"}
