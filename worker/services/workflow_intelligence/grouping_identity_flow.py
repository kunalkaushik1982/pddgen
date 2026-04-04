from __future__ import annotations

from typing import Any

from app.core.observability import get_logger
from app.models.artifact import ArtifactModel
from app.models.process_group import ProcessGroupModel
from worker.services.ai_skills.workflow_group_match.schemas import WorkflowGroupMatchRequest
from worker.services.ai_skills.workflow_title_resolution.schemas import WorkflowTitleResolutionRequest
from worker.services.ai_transcript.interpreter import WorkflowGroupMatchInterpretation, WorkflowTitleInterpretation
from worker.services.generation_types import NoteRecord, StepRecord
from worker.services.workflow_intelligence.grouping_decisions import (
    build_ai_group_match_decision,
    build_heuristic_group_decision,
    heuristic_resolution_confidence,
    resolve_ambiguity_with_ai,
)
from worker.services.workflow_intelligence.grouping_models import (
    CandidateMatchRecord,
    GroupResolutionDecision,
    HeuristicGroupMatchResult,
    TranscriptWorkflowProfile,
)
from worker.services.workflow_intelligence.grouping_summaries import build_workflow_summary
from worker.services.workflow_intelligence.grouping_summary_refresh import serialize_existing_groups_for_ai
from worker.services.workflow_intelligence.grouping_text import slugify

logger = get_logger(__name__)


def resolve_group_identity(
    service: Any,
    *,
    transcript: ArtifactModel,
    steps: list[StepRecord],
    notes: list[NoteRecord],
    existing_groups: list[ProcessGroupModel],
    workflow_profile: TranscriptWorkflowProfile,
    previous_workflow_profile: TranscriptWorkflowProfile | None,
    previous_group: ProcessGroupModel | None,
) -> GroupResolutionDecision:
    if (
        previous_group is not None
        and previous_workflow_profile is not None
        and previous_workflow_profile.boundary_to_next == "same_workflow"
        and previous_workflow_profile.boundary_to_next_confidence in {"medium", "high"}
    ):
        return GroupResolutionDecision(
            inferred_title=previous_group.title,
            inferred_slug=previous_group.canonical_slug,
            matched_group=previous_group,
            decision="continued_previous_group",
            confidence=previous_workflow_profile.boundary_to_next_confidence or "medium",
            decision_source="heuristic",
            is_ambiguous=False,
            rationale=(
                "Reused the previous workflow group because adjacent transcript continuity was classified as "
                f"{previous_workflow_profile.boundary_to_next} with {previous_workflow_profile.boundary_to_next_confidence} confidence."
            ),
            candidate_matches=[{"group_title": previous_group.title, "score": 0.9}],
            supporting_signals=[
                "adjacent_transcript_continuity",
                f"boundary:{previous_workflow_profile.boundary_to_next}",
            ],
        )

    title = service._fallback_title(transcript=transcript, steps=steps, workflow_profile=workflow_profile)
    title_resolution = resolve_title_with_ai(
        service,
        transcript=transcript,
        steps=steps,
        workflow_profile=workflow_profile,
        fallback_title=title,
    )
    title = title_resolution.workflow_title
    slug = title_resolution.canonical_slug
    heuristic_match = service._match_existing_group(
        slug=slug,
        title=title,
        steps=steps,
        workflow_profile=workflow_profile,
        existing_groups=existing_groups,
    )
    ai_group_match = match_existing_group_with_ai(
        service,
        transcript=transcript,
        title_resolution=title_resolution,
        workflow_profile=workflow_profile,
        steps=steps,
        notes=notes,
        existing_groups=existing_groups,
        heuristic_match=heuristic_match,
    )
    if ai_group_match is not None:
        return ai_group_match
    matched_group = heuristic_match["matched_group"]
    ambiguity = heuristic_match["ambiguity"]
    candidate_matches = heuristic_match["candidate_matches"]
    title_supporting_signals = ["ai_title_resolution"] if title_resolution.rationale else []
    if ambiguity and matched_group is None:
        ai_resolution = resolve_ambiguity(
            service,
            transcript=transcript,
            inferred_title=title,
            candidate_matches=candidate_matches,
            steps=steps,
            notes=notes,
            existing_groups=existing_groups,
        )
        if ai_resolution is not None:
            return ai_resolution
    return build_heuristic_group_decision(
        inferred_title=title,
        inferred_slug=slug,
        heuristic_match=heuristic_match,
        title_supporting_signals=title_supporting_signals,
    )


def resolve_title_with_ai(
    service: Any,
    *,
    transcript: ArtifactModel,
    steps: list[StepRecord],
    workflow_profile: TranscriptWorkflowProfile,
    fallback_title: str,
) -> WorkflowTitleInterpretation:
    workflow_summary = build_workflow_summary(
        title=fallback_title,
        workflow_profile=workflow_profile,
        steps=steps,
        notes=[],
    )
    if service._workflow_title_resolution_skill is None:
        service._workflow_title_resolution_skill = service._ai_skill_registry.create("workflow_title_resolution")
    logger.info(
        "Delegating workflow title resolution to AI skill.",
        extra={
            "skill_id": "workflow_title_resolution",
            "skill_version": getattr(service._workflow_title_resolution_skill, "version", "unknown"),
            "transcript_name": transcript.name,
        },
    )
    ai_skill_result = service._workflow_title_resolution_skill.run(
        WorkflowTitleResolutionRequest(
            transcript_name=transcript.name,
            workflow_summary=workflow_summary,
        )
    )
    ai_resolution = (
        None
        if ai_skill_result is None
        else WorkflowTitleInterpretation(
            workflow_title=ai_skill_result.workflow_title,
            canonical_slug=ai_skill_result.canonical_slug,
            confidence=ai_skill_result.confidence,
            rationale=ai_skill_result.rationale,
        )
    )
    if ai_resolution is None or ai_resolution.confidence not in service._ACCEPTED_AI_CONFIDENCE:
        return WorkflowTitleInterpretation(
            workflow_title=fallback_title,
            canonical_slug=slugify(fallback_title),
            confidence="medium",
            rationale="",
        )
    normalized_title = service._normalize_workflow_title(
        base_title=ai_resolution.workflow_title.strip() or fallback_title,
        steps=steps,
        workflow_profile=workflow_profile,
    )
    return WorkflowTitleInterpretation(
        workflow_title=normalized_title,
        canonical_slug=slugify(ai_resolution.canonical_slug or normalized_title or fallback_title),
        confidence=ai_resolution.confidence,
        rationale=ai_resolution.rationale,
    )


def match_existing_group_with_ai(
    service: Any,
    *,
    transcript: ArtifactModel,
    title_resolution: WorkflowTitleInterpretation,
    workflow_profile: TranscriptWorkflowProfile,
    steps: list[StepRecord],
    notes: list[NoteRecord],
    existing_groups: list[ProcessGroupModel],
    heuristic_match: HeuristicGroupMatchResult,
) -> GroupResolutionDecision | None:
    if not existing_groups:
        return None

    workflow_summary = build_workflow_summary(
        title=title_resolution.workflow_title,
        workflow_profile=workflow_profile,
        steps=steps,
        notes=notes,
    )
    serialized_existing_groups = serialize_existing_groups_for_ai(
        existing_groups=existing_groups,
        heuristic_match=heuristic_match,
    )
    if service._workflow_group_match_skill is None:
        service._workflow_group_match_skill = service._ai_skill_registry.create("workflow_group_match")
    logger.info(
        "Delegating workflow group match to AI skill.",
        extra={
            "skill_id": "workflow_group_match",
            "skill_version": getattr(service._workflow_group_match_skill, "version", "unknown"),
            "transcript_name": transcript.name,
        },
    )
    ai_skill_result = service._workflow_group_match_skill.run(
        WorkflowGroupMatchRequest(
            transcript_name=transcript.name,
            workflow_summary=workflow_summary,
            existing_groups=serialized_existing_groups,
        )
    )
    if ai_skill_result is None:
        return None
    matched_existing_title = (
        ai_skill_result.matched_existing_title
        if isinstance(ai_skill_result.matched_existing_title, str)
        else None
    )
    recommended_title = (
        ai_skill_result.recommended_title
        if isinstance(ai_skill_result.recommended_title, str)
        else ""
    )
    recommended_slug = (
        ai_skill_result.recommended_slug
        if isinstance(ai_skill_result.recommended_slug, str)
        else ""
    )
    rationale = (
        ai_skill_result.rationale
        if isinstance(ai_skill_result.rationale, str)
        else ""
    )
    if not recommended_title and matched_existing_title is None:
        return None
    ai_match = WorkflowGroupMatchInterpretation(
        matched_existing_title=matched_existing_title,
        recommended_title=recommended_title,
        recommended_slug=recommended_slug,
        confidence=ai_skill_result.confidence,
        rationale=rationale,
    )

    heuristic_group = heuristic_match["matched_group"]
    heuristic_title = heuristic_group.title if heuristic_group is not None else None
    heuristic_confidence = heuristic_resolution_confidence(heuristic_match)
    heuristic_decision = "matched_existing_group" if heuristic_title is not None else "created_new_group"
    ai_decision = "matched_existing_group" if ai_match.matched_existing_title else "created_new_group"
    conflict_detected = heuristic_title != ai_match.matched_existing_title
    if not conflict_detected:
        return build_ai_group_match_decision(
            ai_match=ai_match,
            fallback_title=title_resolution.workflow_title,
            existing_groups=existing_groups,
            decision_source="ai",
            heuristic_decision=heuristic_decision,
            heuristic_confidence=heuristic_confidence,
            ai_decision=ai_decision,
            ai_confidence=ai_match.confidence,
            conflict_detected=False,
            slugify=slugify,
        )

    if ai_match.confidence == "high" and heuristic_confidence != "high":
        return build_ai_group_match_decision(
            ai_match=ai_match,
            fallback_title=title_resolution.workflow_title,
            existing_groups=existing_groups,
            decision_source="ai_conflict_override",
            heuristic_decision=heuristic_decision,
            heuristic_confidence=heuristic_confidence,
            ai_decision=ai_decision,
            ai_confidence=ai_match.confidence,
            conflict_detected=True,
            slugify=slugify,
            supporting_signals=["ai_group_matcher", "grouping_conflict_detected", "ai_conflict_override"],
            rationale_prefix=(
                f"AI grouping recommendation conflicted with the heuristic {heuristic_decision.replace('_', ' ')} "
                f"decision, so the AI recommendation was used because it had high confidence while the heuristic confidence was {heuristic_confidence}."
            ),
        )

    if heuristic_confidence == "high" and ai_match.confidence != "high":
        return build_heuristic_group_decision(
            inferred_title=title_resolution.workflow_title,
            inferred_slug=title_resolution.canonical_slug,
            heuristic_match=heuristic_match,
            title_supporting_signals=["ai_title_resolution"] if title_resolution.rationale else [],
            decision_source="heuristic_fallback",
            rationale_override=(
                f"AI suggested {'existing workflow ' + ai_match.matched_existing_title if ai_match.matched_existing_title else 'creating a new workflow'}, "
                f"but the heuristic {heuristic_decision.replace('_', ' ')} decision remained stronger, so the heuristic result was kept."
            ),
            heuristic_decision=heuristic_decision,
            heuristic_confidence=heuristic_confidence,
            ai_decision=ai_decision,
            ai_confidence=ai_match.confidence,
            conflict_detected=True,
            extra_supporting_signals=["grouping_conflict_detected", "heuristic_fallback"],
        )

    return build_heuristic_group_decision(
        inferred_title=title_resolution.workflow_title,
        inferred_slug=title_resolution.canonical_slug,
        heuristic_match=heuristic_match,
        title_supporting_signals=["ai_title_resolution"] if title_resolution.rationale else [],
        decision_source="conflict_unresolved",
        force_ambiguous=True,
        rationale_override=(
            f"AI and heuristic grouping both produced credible but conflicting outcomes for '{title_resolution.workflow_title}', "
            "so the system kept the conservative heuristic assignment and marked it ambiguous for later review."
        ),
        heuristic_decision=heuristic_decision,
        heuristic_confidence=heuristic_confidence,
        ai_decision=ai_decision,
        ai_confidence=ai_match.confidence,
        conflict_detected=True,
        extra_supporting_signals=["grouping_conflict_detected", "conflict_unresolved"],
    )


def resolve_ambiguity(
    service: Any,
    *,
    transcript: ArtifactModel,
    inferred_title: str,
    candidate_matches: list[CandidateMatchRecord],
    steps: list[StepRecord],
    notes: list[NoteRecord],
    existing_groups: list[ProcessGroupModel],
) -> GroupResolutionDecision | None:
    ai_resolution = service.ai_transcript_interpreter.resolve_ambiguous_process_group(
        transcript_name=transcript.name,
        inferred_title=inferred_title,
        candidate_matches=candidate_matches,
        steps=steps,
        notes=notes,
    )
    return resolve_ambiguity_with_ai(
        ai_resolution=ai_resolution,
        inferred_title=inferred_title,
        candidate_matches=candidate_matches,
        existing_groups=existing_groups,
        slugify=slugify,
    )
