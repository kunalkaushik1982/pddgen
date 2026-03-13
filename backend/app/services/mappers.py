r"""
Purpose: Mapper helpers for converting ORM entities into API response models.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\mappers.py
"""

import json

from app.models.draft_session import DraftSessionModel
from app.models.process_note import ProcessNoteModel
from app.models.process_step import ProcessStepModel
from app.models.process_step_screenshot_candidate import ProcessStepScreenshotCandidateModel
from app.models.process_step_screenshot import ProcessStepScreenshotModel
from app.schemas.common import EvidenceReference
from app.schemas.draft_session import (
    CandidateScreenshotResponse,
    DraftSessionListItemResponse,
    DraftSessionResponse,
    ProcessNoteResponse,
    ProcessStepResponse,
    StepScreenshotResponse,
)


def _parse_json_list(value: str) -> list:
    """Parse persisted JSON string values into Python lists."""
    if not value:
        return []

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def map_process_step(step: ProcessStepModel) -> ProcessStepResponse:
    """Convert a persisted process step into an API response."""
    evidence_references = [
        EvidenceReference.model_validate(item) for item in _parse_json_list(step.evidence_references)
    ]
    screenshots = [map_step_screenshot(item) for item in sorted(step.step_screenshots, key=lambda screenshot: screenshot.sequence_number)]
    selected_artifact_ids = {item.artifact_id for item in step.step_screenshots}
    candidate_screenshots = [
        map_candidate_screenshot(item, selected_artifact_ids)
        for item in sorted(step.step_screenshot_candidates, key=lambda screenshot: screenshot.sequence_number)
    ]
    return ProcessStepResponse(
        id=step.id,
        step_number=step.step_number,
        application_name=step.application_name,
        action_text=step.action_text,
        source_data_note=step.source_data_note,
        timestamp=step.timestamp,
        start_timestamp=step.start_timestamp,
        end_timestamp=step.end_timestamp,
        supporting_transcript_text=step.supporting_transcript_text,
        screenshot_id=step.screenshot_id,
        confidence=step.confidence,
        evidence_references=evidence_references,
        screenshots=screenshots,
        candidate_screenshots=candidate_screenshots,
        edited_by_ba=step.edited_by_ba,
    )


def map_step_screenshot(step_screenshot: ProcessStepScreenshotModel) -> StepScreenshotResponse:
    """Convert one step screenshot relation into an API response."""
    return StepScreenshotResponse(
        id=step_screenshot.id,
        artifact_id=step_screenshot.artifact_id,
        role=step_screenshot.role,
        sequence_number=step_screenshot.sequence_number,
        timestamp=step_screenshot.timestamp,
        selection_method=step_screenshot.selection_method,
        is_primary=step_screenshot.is_primary,
        artifact=step_screenshot.artifact,
    )


def map_candidate_screenshot(
    candidate_screenshot: ProcessStepScreenshotCandidateModel,
    selected_artifact_ids: set[str],
) -> CandidateScreenshotResponse:
    """Convert one candidate screenshot relation into an API response."""
    return CandidateScreenshotResponse(
        id=candidate_screenshot.id,
        artifact_id=candidate_screenshot.artifact_id,
        sequence_number=candidate_screenshot.sequence_number,
        timestamp=candidate_screenshot.timestamp,
        source_role=candidate_screenshot.source_role,
        selection_method=candidate_screenshot.selection_method,
        is_selected=candidate_screenshot.artifact_id in selected_artifact_ids,
        artifact=candidate_screenshot.artifact,
    )


def map_process_note(note: ProcessNoteModel) -> ProcessNoteResponse:
    """Convert a persisted process note into an API response."""
    return ProcessNoteResponse(
        id=note.id,
        text=note.text,
        related_step_ids=_parse_json_list(note.related_step_ids),
        evidence_reference_ids=_parse_json_list(note.evidence_reference_ids),
        confidence=note.confidence,
        inference_type=note.inference_type,
    )


def map_draft_session(session: DraftSessionModel) -> DraftSessionResponse:
    """Convert a full persisted draft session into an API response."""
    return DraftSessionResponse(
        id=session.id,
        title=session.title,
        status=session.status,
        owner_id=session.owner_id,
        created_at=session.created_at,
        updated_at=session.updated_at,
        artifacts=session.artifacts,
        process_steps=[map_process_step(step) for step in sorted(session.process_steps, key=lambda item: item.step_number)],
        process_notes=[map_process_note(note) for note in session.process_notes],
        output_documents=session.output_documents,
    )


def map_draft_session_list_item(session: DraftSessionModel) -> DraftSessionListItemResponse:
    """Convert one draft session into a compact history-list item."""
    return DraftSessionListItemResponse(
        id=session.id,
        title=session.title,
        status=session.status,
        owner_id=session.owner_id,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )
