from __future__ import annotations

from app.models.artifact import ArtifactModel
from app.models.draft_session import DraftSessionModel
from app.models.process_group import ProcessGroupModel
from worker.services.generation_types import NoteRecord, StepRecord
from worker.services.workflow_intelligence import EvidenceSegment, WorkflowBoundaryDecision
from worker.services.workflow_intelligence.grouping_models import ProcessGroupingResult, TranscriptWorkflowProfile


def assign_groups(
    *,
    service,
    db,
    session: DraftSessionModel,
    transcript_artifacts: list[ArtifactModel],
    steps_by_transcript: dict[str, list[StepRecord]],
    notes_by_transcript: dict[str, list[NoteRecord]],
    evidence_segments: list[EvidenceSegment],
    workflow_boundary_decisions: list[WorkflowBoundaryDecision],
) -> ProcessGroupingResult:
    process_groups: list[ProcessGroupModel] = []
    transcript_group_ids: dict[str, str] = {}
    assignment_details: list[dict[str, object]] = []
    workflow_profiles = service._build_transcript_profiles(  # noqa: SLF001
        evidence_segments=evidence_segments,
        workflow_boundary_decisions=workflow_boundary_decisions,
        steps_by_transcript=steps_by_transcript,
    )
    sorted_transcripts = service._sort_transcripts(transcript_artifacts)  # noqa: SLF001

    for index, transcript in enumerate(sorted_transcripts):
        transcript_steps = steps_by_transcript.get(transcript.id, [])
        transcript_notes = notes_by_transcript.get(transcript.id, [])
        workflow_profile = workflow_profiles.get(
            transcript.id,
            TranscriptWorkflowProfile(
                transcript_artifact_id=transcript.id,
                top_actors=[],
                top_objects=[],
                top_systems=[],
                top_applications=[],
                top_actions=[],
                top_goals=[],
                top_rules=[],
                top_domain_terms=[],
            ),
        )
        previous_transcript = sorted_transcripts[index - 1] if index > 0 else None
        previous_group = process_groups[-1] if process_groups else None
        previous_workflow_profile = workflow_profiles.get(previous_transcript.id) if previous_transcript is not None else None
        resolution = service._resolve_group_identity(  # noqa: SLF001
            transcript=transcript,
            steps=transcript_steps,
            notes=transcript_notes,
            existing_groups=process_groups,
            workflow_profile=workflow_profile,
            previous_workflow_profile=previous_workflow_profile,
            previous_group=previous_group,
        )
        matched_group = resolution.matched_group

        if matched_group is None:
            matched_group = service.process_group_service.create_process_group(
                db,
                session=session,
                title=resolution.inferred_title,
                canonical_slug=resolution.inferred_slug,
                display_order=len(process_groups) + 1,
            )
            process_groups.append(matched_group)

        matched_group.summary_text = service._group_summary_seed(  # noqa: SLF001
            inferred_title=resolution.inferred_title,
            steps=transcript_steps,
            notes=transcript_notes,
            workflow_profile=workflow_profile,
        )
        db.commit()

        transcript_group_ids[transcript.id] = matched_group.id
        assignment_details.append(
            {
                "transcript_name": transcript.name,
                "inferred_workflow": resolution.inferred_title,
                "assigned_group_id": matched_group.id,
                "assigned_group_title": matched_group.title,
                "decision": resolution.decision,
                "decision_confidence": resolution.confidence,
                "decision_source": resolution.decision_source,
                "is_ambiguous": resolution.is_ambiguous,
                "rationale": resolution.rationale,
                "candidate_matches": resolution.candidate_matches,
                "supporting_signals": resolution.supporting_signals,
                "heuristic_decision": resolution.heuristic_decision,
                "heuristic_confidence": resolution.heuristic_confidence,
                "ai_decision": resolution.ai_decision,
                "ai_confidence": resolution.ai_confidence,
                "conflict_detected": resolution.conflict_detected,
                "top_goals": workflow_profile.top_goals,
                "top_objects": workflow_profile.top_objects,
                "top_systems": workflow_profile.top_systems,
                "top_applications": workflow_profile.top_applications,
                "top_actors": workflow_profile.top_actors,
                "top_rules": workflow_profile.top_rules,
                "capability_tags": service._parse_capability_tags(getattr(matched_group, "capability_tags_json", "[]")),  # noqa: SLF001
            }
        )
        for step in transcript_steps:
            step["process_group_id"] = matched_group.id
        for note in transcript_notes:
            note["process_group_id"] = matched_group.id

    service._refresh_group_summaries(  # noqa: SLF001
        process_groups=process_groups,
        transcript_group_ids=transcript_group_ids,
        steps_by_transcript=steps_by_transcript,
        notes_by_transcript=notes_by_transcript,
        workflow_profiles=workflow_profiles,
        document_type=getattr(session, "document_type", "pdd"),
    )
    capability_tags_by_group = {
        group.id: service._parse_capability_tags(getattr(group, "capability_tags_json", "[]"))  # noqa: SLF001
        for group in process_groups
    }
    for assignment in assignment_details:
        assigned_group_id = str(assignment.get("assigned_group_id", "") or "")
        if assigned_group_id:
            assignment["capability_tags"] = capability_tags_by_group.get(assigned_group_id, [])

    return ProcessGroupingResult(
        process_groups=process_groups,
        transcript_group_ids=transcript_group_ids,
        assignment_details=assignment_details,
    )
