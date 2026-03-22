r"""
Purpose: Mapper helpers for converting ORM entities into API response models.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\mappers.py
"""

import json

from app.models.draft_session import DraftSessionModel
from app.models.process_group import ProcessGroupModel
from app.models.process_note import ProcessNoteModel
from app.models.process_step import ProcessStepModel
from app.models.process_step_screenshot_candidate import ProcessStepScreenshotCandidateModel
from app.models.process_step_screenshot import ProcessStepScreenshotModel
from app.schemas.common import EvidenceReference
from app.schemas.draft_session import (
    ActionLogResponse,
    CandidateScreenshotResponse,
    DraftSessionListItemResponse,
    DraftSessionResponse,
    ProcessNoteResponse,
    ProcessGroupResponse,
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


def _has_required_uploads(session: DraftSessionModel) -> bool:
    kinds = {artifact.kind for artifact in session.artifacts}
    return {"video", "transcript", "template"}.issubset(kinds)


def _latest_action_log_by_type(session: DraftSessionModel, event_type: str):
    return next(
        (
            item
            for item in sorted(session.action_logs, key=lambda action_log: action_log.created_at, reverse=True)
            if item.event_type == event_type
        ),
        None,
    )


def _latest_stage_info(session: DraftSessionModel) -> tuple[str, str]:
    latest_action_log = next(
        iter(sorted(session.action_logs, key=lambda action_log: action_log.created_at, reverse=True)),
        None,
    )

    if session.status == "failed":
        failure_log = _latest_action_log_by_type(session, "generation_failed")
        return "Run failed", failure_log.detail if failure_log is not None else "Generation failed."

    if session.status == "processing":
        stage_log = next(
            (
                item
                for item in sorted(session.action_logs, key=lambda action_log: action_log.created_at, reverse=True)
                if item.event_type in {"generation_stage", "generation_queued"}
            ),
            None,
        )
        if stage_log is not None:
            return stage_log.title, stage_log.detail
        return "Generation in progress", "Draft generation is running."

    if session.status == "draft" and _has_required_uploads(session):
        return "Inputs uploaded", "Upload complete. Resume this draft to start generation."

    if session.status == "review":
        if latest_action_log is not None and latest_action_log.event_type in {
            "screenshot_generation_queued",
            "generation_stage",
            "screenshots_generated",
        }:
            return latest_action_log.title, latest_action_log.detail
        return "Ready for review", "Draft generation completed successfully."

    if session.status == "exported":
        return "Export completed", "A document export is available for this run."

    return "Session created", "Session created."


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
        process_group_id=step.process_group_id,
        meeting_id=step.meeting_id,
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
        process_group_id=note.process_group_id,
        meeting_id=note.meeting_id,
        text=note.text,
        related_step_ids=_parse_json_list(note.related_step_ids),
        evidence_reference_ids=_parse_json_list(note.evidence_reference_ids),
        confidence=note.confidence,
        inference_type=note.inference_type,
    )


def map_action_log(action_log) -> ActionLogResponse:
    """Convert one persisted action log row into an API response."""
    return ActionLogResponse.model_validate(action_log)


def map_process_group(process_group: ProcessGroupModel) -> ProcessGroupResponse:
    """Convert one persisted process group into an API response."""
    return ProcessGroupResponse.model_validate(process_group)


def map_draft_session(session: DraftSessionModel) -> DraftSessionResponse:
    """Convert a full persisted draft session into an API response."""
    return DraftSessionResponse(
        id=session.id,
        title=session.title,
        status=session.status,
        owner_id=session.owner_id,
        diagram_type=session.diagram_type,
        created_at=session.created_at,
        updated_at=session.updated_at,
        process_groups=[map_process_group(group) for group in sorted(session.process_groups, key=lambda item: item.display_order)],
        artifacts=session.artifacts,
        process_steps=[map_process_step(step) for step in sorted(session.process_steps, key=lambda item: item.step_number)],
        process_notes=[map_process_note(note) for note in session.process_notes],
        output_documents=session.output_documents,
        action_logs=[map_action_log(item) for item in sorted(session.action_logs, key=lambda item: item.created_at, reverse=True)],
    )


def map_draft_session_list_item(session: DraftSessionModel) -> DraftSessionListItemResponse:
    """Convert one draft session into a compact history-list item."""
    latest_stage_title, latest_stage_detail = _latest_stage_info(session)
    failure_log = _latest_action_log_by_type(session, "generation_failed")
    failure_detail = failure_log.detail if session.status == "failed" and failure_log is not None else ""
    return DraftSessionListItemResponse(
        id=session.id,
        title=session.title,
        status=session.status,
        owner_id=session.owner_id,
        diagram_type=session.diagram_type,
        created_at=session.created_at,
        updated_at=session.updated_at,
        latest_stage_title=latest_stage_title,
        latest_stage_detail=latest_stage_detail,
        failure_detail=failure_detail,
        resume_ready=session.status == "draft" and _has_required_uploads(session),
        can_retry=session.status == "failed",
    )
