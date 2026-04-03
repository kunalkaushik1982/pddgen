from __future__ import annotations

from collections import Counter, defaultdict

from app.models.artifact import ArtifactModel
from worker.services.generation_types import NoteRecord, StepRecord
from worker.services.workflow_intelligence import EvidenceSegment, WorkflowBoundaryDecision
from worker.services.workflow_intelligence.grouping_models import TranscriptWorkflowProfile
from worker.services.workflow_intelligence.grouping_title_resolution import extract_leading_action_verb, operation_signature_from_steps


def sort_transcripts(transcript_artifacts: list[ArtifactModel]) -> list[ArtifactModel]:
    return sorted(
        transcript_artifacts,
        key=lambda artifact: (
            meeting.order_index
            if (meeting := getattr(artifact, "meeting", None)) is not None and meeting.order_index is not None
            else 1_000_000,
            meeting_date.isoformat()
            if (meeting := getattr(artifact, "meeting", None)) is not None
            and (meeting_date := getattr(meeting, "meeting_date", None)) is not None
            else "",
            uploaded_at.isoformat()
            if (meeting := getattr(artifact, "meeting", None)) is not None
            and (uploaded_at := getattr(meeting, "uploaded_at", None)) is not None
            else "",
            artifact.id,
        ),
    )


def build_workflow_summary(
    *,
    title: str,
    workflow_profile: TranscriptWorkflowProfile,
    steps: list[StepRecord],
    notes: list[NoteRecord],
) -> dict[str, object]:
    return {
        "suggested_title": title,
        "top_actors": workflow_profile.top_actors,
        "top_objects": workflow_profile.top_objects,
        "top_systems": workflow_profile.top_systems,
        "top_applications": workflow_profile.top_applications,
        "top_actions": workflow_profile.top_actions,
        "top_goals": workflow_profile.top_goals,
        "top_rules": workflow_profile.top_rules,
        "top_domain_terms": workflow_profile.top_domain_terms,
        "operational_signature": operation_signature_from_steps(steps),
        "step_samples": [
            {
                "action_text": str(step.get("action_text", "") or ""),
                "supporting_transcript_text": str(step.get("supporting_transcript_text", "") or ""),
            }
            for step in steps[:8]
        ],
        "note_samples": [str(note.get("text", "") or "") for note in notes[:4]],
    }


def build_transcript_profiles(
    *,
    evidence_segments: list[EvidenceSegment],
    workflow_boundary_decisions: list[WorkflowBoundaryDecision],
    steps_by_transcript: dict[str, list[StepRecord]],
) -> dict[str, TranscriptWorkflowProfile]:
    segments_by_id = {segment.id: segment for segment in evidence_segments}
    object_counts: dict[str, Counter[str]] = defaultdict(Counter)
    actor_counts: dict[str, Counter[str]] = defaultdict(Counter)
    system_counts: dict[str, Counter[str]] = defaultdict(Counter)
    application_counts: dict[str, Counter[str]] = defaultdict(Counter)
    action_counts: dict[str, Counter[str]] = defaultdict(Counter)
    goal_counts: dict[str, Counter[str]] = defaultdict(Counter)
    rule_counts: dict[str, Counter[str]] = defaultdict(Counter)
    domain_term_counts: dict[str, Counter[str]] = defaultdict(Counter)

    for segment in evidence_segments:
        enrichment = segment.enrichment
        if enrichment is None:
            continue
        transcript_id = segment.transcript_artifact_id
        if enrichment.actor:
            actor_counts[transcript_id][enrichment.actor] += 1
        if enrichment.business_object:
            object_counts[transcript_id][enrichment.business_object] += 1
        if enrichment.system_name:
            system_counts[transcript_id][enrichment.system_name] += 1
        if enrichment.action_verb:
            action_counts[transcript_id][enrichment.action_verb] += 1
        if enrichment.workflow_goal:
            goal_counts[transcript_id][enrichment.workflow_goal] += 1
        for rule_hint in enrichment.rule_hints:
            rule_counts[transcript_id][rule_hint] += 1
        for domain_term in enrichment.domain_terms:
            domain_term_counts[transcript_id][domain_term] += 1

    for transcript_id, steps in steps_by_transcript.items():
        for step in steps:
            application_name = str(step.get("application_name", "") or "").strip()
            if application_name:
                application_counts[transcript_id][application_name] += 1
            action_text = str(step.get("action_text", "") or "").strip()
            leading_action = extract_leading_action_verb(action_text)
            if leading_action:
                action_counts[transcript_id][leading_action] += 1

    boundary_map: dict[str, tuple[str, str]] = {}
    for decision in workflow_boundary_decisions:
        left_segment = segments_by_id.get(decision.left_segment_id)
        right_segment = segments_by_id.get(decision.right_segment_id)
        if left_segment is None or right_segment is None:
            continue
        if left_segment.transcript_artifact_id == right_segment.transcript_artifact_id:
            continue
        boundary_map[left_segment.transcript_artifact_id] = (decision.decision, decision.confidence)

    transcript_ids = {segment.transcript_artifact_id for segment in evidence_segments} | set(steps_by_transcript)
    profiles: dict[str, TranscriptWorkflowProfile] = {}
    for transcript_id in transcript_ids:
        boundary = boundary_map.get(transcript_id)
        profiles[transcript_id] = TranscriptWorkflowProfile(
            transcript_artifact_id=transcript_id,
            top_actors=[value for value, _ in actor_counts[transcript_id].most_common(3)],
            top_objects=[value for value, _ in object_counts[transcript_id].most_common(3)],
            top_systems=[value for value, _ in system_counts[transcript_id].most_common(3)],
            top_applications=[value for value, _ in application_counts[transcript_id].most_common(3)],
            top_actions=[value for value, _ in action_counts[transcript_id].most_common(3)],
            top_goals=[value for value, _ in goal_counts[transcript_id].most_common(3)],
            top_rules=[value for value, _ in rule_counts[transcript_id].most_common(2)],
            top_domain_terms=[value for value, _ in domain_term_counts[transcript_id].most_common(4)],
            boundary_to_next=boundary[0] if boundary else None,
            boundary_to_next_confidence=boundary[1] if boundary else None,
        )
    return profiles
