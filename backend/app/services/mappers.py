r"""
Purpose: Mapper helpers for converting ORM entities into API response models.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\mappers.py
"""

import json
from datetime import datetime, timezone

from app.api.dependencies import get_storage_service
from app.core.config import get_settings
from app.services.generation_timing import wall_duration_seconds
from app.models.action_log import ActionLogModel
from app.models.artifact import ArtifactModel
from app.models.draft_session import DraftSessionModel
from app.models.process_group import ProcessGroupModel
from app.models.process_note import ProcessNoteModel
from app.models.process_step import ProcessStepModel
from app.models.process_step_screenshot_candidate import ProcessStepScreenshotCandidateModel
from app.models.process_step_screenshot import ProcessStepScreenshotModel
from app.schemas.common import EvidenceReference
from app.schemas.draft_session import (
    ActionLogResponse,
    ArtifactResponse,
    CandidateScreenshotResponse,
    DraftSessionListItemResponse,
    DraftSessionResponse,
    PendingEvidenceBundleResponse,
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


def _parse_json_object(value: str) -> dict:
    """Parse persisted JSON object values into Python dictionaries."""
    if not value:
        return {}

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


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


def _latest_successful_draft_at(session: DraftSessionModel) -> datetime | None:
    draft_generated_log = _latest_action_log_by_type(session, "draft_generated")
    if draft_generated_log is not None:
        return draft_generated_log.created_at
    if session.status in {"review", "exported"} and session.process_steps:
        return session.updated_at
    return None


def _is_effectively_pending_bundle(session: DraftSessionModel, bundle) -> bool:
    if bundle.status != "pending" or bundle.meeting is None:
        return False
    processed_meeting_ids = {step.meeting_id for step in session.process_steps if step.meeting_id}
    processed_meeting_ids.update(note.meeting_id for note in session.process_notes if note.meeting_id)
    if bundle.meeting_id in processed_meeting_ids:
        return False

    processed_transcript_ids = {
        step.source_transcript_artifact_id for step in session.process_steps if step.source_transcript_artifact_id
    }
    if bundle.transcript_artifact_id and bundle.transcript_artifact_id in processed_transcript_ids:
        return False

    latest_successful_draft_at = _latest_successful_draft_at(session)
    if latest_successful_draft_at is None:
        return True
    return bundle.created_at > latest_successful_draft_at


def _maybe_stale_extracting_screenshots_log(
    log: ActionLogModel | None,
    *,
    stale_after_seconds: float,
) -> tuple[str, str] | None:
    """If this log is an aged 'Extracting screenshots' stage, surface a stalled UX message."""
    if log is None or stale_after_seconds <= 0:
        return None
    if log.event_type != "generation_stage":
        return None
    if log.title.strip().lower() != "extracting screenshots":
        return None
    created = log.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    age_seconds = (datetime.now(timezone.utc) - created).total_seconds()
    if age_seconds <= stale_after_seconds:
        return None
    return (
        "Screenshot run stalled",
        "The last screenshot run did not finish in time. Click Generate SS to retry.",
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
        settings = get_settings()
        stage_log = next(
            (
                item
                for item in sorted(session.action_logs, key=lambda action_log: action_log.created_at, reverse=True)
                if item.event_type in {"generation_stage", "generation_queued", "screenshot_generation_queued"}
            ),
            None,
        )
        if stage_log is not None:
            stale = _maybe_stale_extracting_screenshots_log(
                stage_log,
                stale_after_seconds=settings.screenshot_extraction_stale_after_seconds,
            )
            if stale is not None:
                return stale
            return stage_log.title, stage_log.detail
        return "Generation in progress", "Draft generation is running."

    if session.status == "draft" and _has_required_uploads(session):
        return "Inputs uploaded", "Upload complete. Resume this draft to start generation."

    if session.status == "review":
        settings = get_settings()
        if latest_action_log is not None and latest_action_log.event_type in {
            "screenshot_generation_queued",
            "generation_stage",
            "screenshots_generated",
            "screenshot_generation_failed",
        }:
            stale = _maybe_stale_extracting_screenshots_log(
                latest_action_log,
                stale_after_seconds=settings.screenshot_extraction_stale_after_seconds,
            )
            if stale is not None:
                return stale
            return latest_action_log.title, latest_action_log.detail
        return "Ready for review", "Draft generation completed successfully."

    if session.status == "exported":
        return "Export completed", "A document export is available for this run."

    return "Session created", "Session created."


def _is_previewable_artifact(artifact: ArtifactModel) -> bool:
    content_type = (artifact.content_type or "").lower()
    return content_type.startswith("image/") or content_type == "application/pdf"


def map_artifact(artifact: ArtifactModel, storage_service=None) -> ArtifactResponse:
    """Convert one persisted artifact into an API response with preview metadata when available."""
    preview_url = None
    preview_expires_at = None
    if _is_previewable_artifact(artifact):
        service = storage_service or get_storage_service()
        descriptor = service.build_preview_descriptor(artifact)
        preview_url = descriptor.url
        preview_expires_at = descriptor.expires_at

    return ArtifactResponse(
        id=artifact.id,
        meeting_id=artifact.meeting_id,
        upload_batch_id=artifact.upload_batch_id,
        upload_pair_index=artifact.upload_pair_index,
        name=artifact.name,
        kind=artifact.kind,
        storage_path=artifact.storage_path,
        content_type=artifact.content_type,
        preview_url=preview_url,
        preview_expires_at=preview_expires_at,
        size_bytes=artifact.size_bytes,
        created_at=artifact.created_at,
    )


def map_process_step(step: ProcessStepModel, storage_service=None) -> ProcessStepResponse:
    """Convert a persisted process step into an API response."""
    evidence_references = [
        EvidenceReference.model_validate(item) for item in _parse_json_list(step.evidence_references)
    ]
    screenshots = [
        map_step_screenshot(item, storage_service=storage_service)
        for item in sorted(step.step_screenshots, key=lambda screenshot: screenshot.sequence_number)
    ]
    selected_artifact_ids = {item.artifact_id for item in step.step_screenshots}
    candidate_screenshots = [
        map_candidate_screenshot(item, selected_artifact_ids, storage_service=storage_service)
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


def map_step_screenshot(step_screenshot: ProcessStepScreenshotModel, storage_service=None) -> StepScreenshotResponse:
    """Convert one step screenshot relation into an API response."""
    return StepScreenshotResponse(
        id=step_screenshot.id,
        artifact_id=step_screenshot.artifact_id,
        role=step_screenshot.role,
        sequence_number=step_screenshot.sequence_number,
        timestamp=step_screenshot.timestamp,
        selection_method=step_screenshot.selection_method,
        is_primary=step_screenshot.is_primary,
        artifact=map_artifact(step_screenshot.artifact, storage_service=storage_service),
    )


def map_candidate_screenshot(
    candidate_screenshot: ProcessStepScreenshotCandidateModel,
    selected_artifact_ids: set[str],
    storage_service=None,
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
        artifact=map_artifact(candidate_screenshot.artifact, storage_service=storage_service),
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
    return ActionLogResponse(
        id=action_log.id,
        event_type=action_log.event_type,
        title=action_log.title,
        detail=action_log.detail,
        metadata=_parse_json_object(getattr(action_log, "metadata_json", "")),
        actor=action_log.actor,
        created_at=action_log.created_at,
    )


def map_process_group(process_group: ProcessGroupModel) -> ProcessGroupResponse:
    """Convert one persisted process group into an API response."""
    return ProcessGroupResponse(
        id=process_group.id,
        session_id=process_group.session_id,
        title=process_group.title,
        canonical_slug=process_group.canonical_slug,
        status=process_group.status,
        display_order=process_group.display_order,
        summary_text=process_group.summary_text,
        capability_tags=[str(item) for item in _parse_json_list(getattr(process_group, "capability_tags_json", "[]")) if isinstance(item, str)],
        overview_diagram_json=process_group.overview_diagram_json,
        detailed_diagram_json=process_group.detailed_diagram_json,
    )


def map_draft_session(session: DraftSessionModel) -> DraftSessionResponse:
    """Convert a full persisted draft session into an API response."""
    storage_service = get_storage_service()
    artifacts_by_id = {artifact.id: artifact for artifact in session.artifacts}
    pending_bundles: list[PendingEvidenceBundleResponse] = []
    for bundle in session.meeting_evidence_bundles:
        if not _is_effectively_pending_bundle(session, bundle):
            continue
        transcript_artifact = artifacts_by_id.get(bundle.transcript_artifact_id or "")
        video_artifact = artifacts_by_id.get(bundle.video_artifact_id or "")
        pending_bundles.append(
            PendingEvidenceBundleResponse(
                id=bundle.id,
                meeting_id=bundle.meeting.id,
                meeting_title=bundle.meeting.title,
                uploaded_at=bundle.created_at,
                pair_index=bundle.pair_index,
                transcript_artifact_id=bundle.transcript_artifact_id,
                transcript_name=transcript_artifact.name if transcript_artifact is not None else None,
                video_artifact_id=bundle.video_artifact_id,
                video_name=video_artifact.name if video_artifact is not None else None,
            )
        )
    return DraftSessionResponse(
        id=session.id,
        title=session.title,
        status=session.status,
        owner_id=session.owner_id,
        diagram_type=session.diagram_type,
        document_type=session.document_type,
        created_at=session.created_at,
        updated_at=session.updated_at,
        draft_generation_started_at=session.draft_generation_started_at,
        draft_generation_completed_at=session.draft_generation_completed_at,
        screenshot_generation_started_at=session.screenshot_generation_started_at,
        screenshot_generation_completed_at=session.screenshot_generation_completed_at,
        draft_generation_duration_seconds=wall_duration_seconds(
            session.draft_generation_started_at,
            session.draft_generation_completed_at,
        ),
        screenshot_generation_duration_seconds=wall_duration_seconds(
            session.screenshot_generation_started_at,
            session.screenshot_generation_completed_at,
        ),
        has_unprocessed_evidence=bool(pending_bundles),
        pending_evidence_bundles=sorted(pending_bundles, key=lambda item: item.uploaded_at, reverse=True),
        process_groups=[map_process_group(group) for group in sorted(session.process_groups, key=lambda item: item.display_order)],
        artifacts=[map_artifact(artifact, storage_service=storage_service) for artifact in session.artifacts],
        process_steps=[
            map_process_step(step, storage_service=storage_service)
            for step in sorted(session.process_steps, key=lambda item: item.step_number)
        ],
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
        document_type=session.document_type,
        created_at=session.created_at,
        updated_at=session.updated_at,
        draft_generation_started_at=session.draft_generation_started_at,
        draft_generation_completed_at=session.draft_generation_completed_at,
        screenshot_generation_started_at=session.screenshot_generation_started_at,
        screenshot_generation_completed_at=session.screenshot_generation_completed_at,
        draft_generation_duration_seconds=wall_duration_seconds(
            session.draft_generation_started_at,
            session.draft_generation_completed_at,
        ),
        screenshot_generation_duration_seconds=wall_duration_seconds(
            session.screenshot_generation_started_at,
            session.screenshot_generation_completed_at,
        ),
        latest_stage_title=latest_stage_title,
        latest_stage_detail=latest_stage_detail,
        failure_detail=failure_detail,
        resume_ready=session.status == "draft" and _has_required_uploads(session),
        can_retry=session.status == "failed",
    )
