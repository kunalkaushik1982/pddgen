from __future__ import annotations

from typing import Any, Protocol

from app.models.artifact import ArtifactModel
from app.models.process_group import ProcessGroupModel
from worker.services.ai_skills.workflow_capability_tagging.schemas import WorkflowCapabilityTaggingRequest
from worker.services.ai_skills.workflow_group_match.schemas import WorkflowGroupMatchRequest
from worker.services.ai_skills.workflow_title_resolution.schemas import WorkflowTitleResolutionRequest
from worker.services.ai_transcript.interpreter import WorkflowGroupMatchInterpretation, WorkflowTitleInterpretation
from worker.services.generation_types import NoteRecord, StepRecord
from worker.services.workflow_intelligence.grouping_models import (
    CandidateMatchRecord,
    GroupResolutionDecision,
    HeuristicGroupMatchResult,
    TranscriptWorkflowProfile,
)


class GroupingAIResolutionService(Protocol):
    _ACCEPTED_AI_CONFIDENCE: set[str]
    _ai_skill_registry: Any
    _workflow_title_resolution_skill: Any
    _workflow_group_match_skill: Any
    _workflow_capability_tagging_skill: Any
    ai_transcript_interpreter: Any

    def _build_workflow_summary(
        self,
        *,
        title: str,
        workflow_profile: TranscriptWorkflowProfile,
        steps: list[StepRecord],
        notes: list[NoteRecord],
    ) -> dict[str, object]: ...

    def _serialize_existing_groups_for_ai(
        self,
        *,
        existing_groups: list[ProcessGroupModel],
        heuristic_match: HeuristicGroupMatchResult,
    ) -> list[dict[str, object]]: ...

    def _slugify(self, value: str) -> str: ...

    def _normalize_workflow_title(
        self,
        *,
        base_title: str,
        steps: list[StepRecord],
        workflow_profile: TranscriptWorkflowProfile,
    ) -> str: ...

    def _heuristic_resolution_confidence(self, heuristic_match: HeuristicGroupMatchResult) -> str: ...

    def _build_ai_group_match_decision(
        self,
        *,
        ai_match: WorkflowGroupMatchInterpretation,
        fallback_title: str,
        existing_groups: list[ProcessGroupModel],
        decision_source: str,
        heuristic_decision: str | None,
        heuristic_confidence: str | None,
        ai_decision: str,
        ai_confidence: str,
        conflict_detected: bool,
        supporting_signals: list[str] | None = None,
        rationale_prefix: str = "",
    ) -> GroupResolutionDecision: ...

    def _build_heuristic_group_decision(
        self,
        *,
        inferred_title: str,
        inferred_slug: str,
        heuristic_match: HeuristicGroupMatchResult,
        title_supporting_signals: list[str],
        decision_source: str = "heuristic",
        force_ambiguous: bool = False,
        rationale_override: str | None = None,
        heuristic_decision: str | None = None,
        heuristic_confidence: str | None = None,
        ai_decision: str | None = None,
        ai_confidence: str | None = None,
        conflict_detected: bool = False,
        extra_supporting_signals: list[str] | None = None,
    ) -> GroupResolutionDecision: ...

    def _normalize_capability_tags(self, tags: list[str], *, process_title: str) -> list[str]: ...

    def _fallback_capability_tags(self, *, workflow_profiles: list[TranscriptWorkflowProfile]) -> list[str]: ...


def resolve_title_with_ai(
    service: GroupingAIResolutionService,
    *,
    transcript: ArtifactModel,
    steps: list[StepRecord],
    workflow_profile: TranscriptWorkflowProfile,
    fallback_title: str,
) -> WorkflowTitleInterpretation:
    workflow_summary = service._build_workflow_summary(
        title=fallback_title,
        workflow_profile=workflow_profile,
        steps=steps,
        notes=[],
    )
    if service._workflow_title_resolution_skill is None:
        service._workflow_title_resolution_skill = service._ai_skill_registry.create("workflow_title_resolution")
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
            canonical_slug=service._slugify(fallback_title),
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
        canonical_slug=service._slugify(ai_resolution.canonical_slug or normalized_title or fallback_title),
        confidence=ai_resolution.confidence,
        rationale=ai_resolution.rationale,
    )


def match_existing_group_with_ai(
    service: GroupingAIResolutionService,
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

    workflow_summary = service._build_workflow_summary(
        title=title_resolution.workflow_title,
        workflow_profile=workflow_profile,
        steps=steps,
        notes=notes,
    )
    serialized_existing_groups = service._serialize_existing_groups_for_ai(
        existing_groups=existing_groups,
        heuristic_match=heuristic_match,
    )
    if service._workflow_group_match_skill is None:
        service._workflow_group_match_skill = service._ai_skill_registry.create("workflow_group_match")
    ai_skill_result = service._workflow_group_match_skill.run(
        WorkflowGroupMatchRequest(
            transcript_name=transcript.name,
            workflow_summary=workflow_summary,
            existing_groups=serialized_existing_groups,
        )
    )
    if ai_skill_result is None:
        return None
    if not ai_skill_result.recommended_title and ai_skill_result.matched_existing_title is None:
        return None
    ai_match = WorkflowGroupMatchInterpretation(
        matched_existing_title=ai_skill_result.matched_existing_title,
        recommended_title=ai_skill_result.recommended_title,
        recommended_slug=ai_skill_result.recommended_slug,
        confidence=ai_skill_result.confidence,
        rationale=ai_skill_result.rationale,
    )

    heuristic_group = heuristic_match["matched_group"]
    heuristic_title = heuristic_group.title if heuristic_group is not None else None
    heuristic_confidence = service._heuristic_resolution_confidence(heuristic_match)
    heuristic_decision = "matched_existing_group" if heuristic_title is not None else "created_new_group"
    ai_decision = "matched_existing_group" if ai_match.matched_existing_title else "created_new_group"
    conflict_detected = heuristic_title != ai_match.matched_existing_title
    if not conflict_detected:
        return service._build_ai_group_match_decision(
            ai_match=ai_match,
            fallback_title=title_resolution.workflow_title,
            existing_groups=existing_groups,
            decision_source="ai",
            heuristic_decision=heuristic_decision,
            heuristic_confidence=heuristic_confidence,
            ai_decision=ai_decision,
            ai_confidence=ai_match.confidence,
            conflict_detected=False,
        )

    if ai_match.confidence == "high" and heuristic_confidence != "high":
        return service._build_ai_group_match_decision(
            ai_match=ai_match,
            fallback_title=title_resolution.workflow_title,
            existing_groups=existing_groups,
            decision_source="ai_conflict_override",
            heuristic_decision=heuristic_decision,
            heuristic_confidence=heuristic_confidence,
            ai_decision=ai_decision,
            ai_confidence=ai_match.confidence,
            conflict_detected=True,
            supporting_signals=["ai_group_matcher", "grouping_conflict_detected", "ai_conflict_override"],
            rationale_prefix=(
                f"AI grouping recommendation conflicted with the heuristic {heuristic_decision.replace('_', ' ')} "
                f"decision, so the AI recommendation was used because it had high confidence while the heuristic confidence was {heuristic_confidence}."
            ),
        )

    if heuristic_confidence == "high" and ai_match.confidence != "high":
        return service._build_heuristic_group_decision(
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

    return service._build_heuristic_group_decision(
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


def resolve_ambiguity_with_ai(
    service: GroupingAIResolutionService,
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
    if ai_resolution is None:
        return None

    matched_group = next(
        (group for group in existing_groups if group.title == ai_resolution.matched_existing_title),
        None,
    )
    resolved_title = ai_resolution.recommended_title.strip() or inferred_title
    resolved_slug = service._slugify(ai_resolution.recommended_slug or resolved_title)
    if matched_group is not None:
        return GroupResolutionDecision(
            inferred_title=resolved_title,
            inferred_slug=resolved_slug,
            matched_group=matched_group,
            decision="ai_resolved_ambiguous_match",
            confidence=ai_resolution.confidence,
            decision_source="ai_tiebreak",
            is_ambiguous=False,
            rationale=ai_resolution.rationale or f"AI resolved the ambiguity in favor of existing workflow '{matched_group.title}'.",
            candidate_matches=candidate_matches,
            supporting_signals=["ai_ambiguity_resolution"],
        )
    return GroupResolutionDecision(
        inferred_title=resolved_title,
        inferred_slug=resolved_slug,
        matched_group=None,
        decision="ai_resolved_ambiguous_new_group",
        confidence=ai_resolution.confidence,
        decision_source="ai_tiebreak",
        is_ambiguous=False,
        rationale=ai_resolution.rationale or f"AI resolved the ambiguity in favor of creating a new workflow '{resolved_title}'.",
        candidate_matches=candidate_matches,
        supporting_signals=["ai_ambiguity_resolution"],
    )


def resolve_capability_tags(
    service: GroupingAIResolutionService,
    *,
    process_title: str,
    workflow_summary: dict[str, object],
    workflow_profiles: list[TranscriptWorkflowProfile],
    document_type: str,
) -> list[str]:
    if service._workflow_capability_tagging_skill is None:
        service._workflow_capability_tagging_skill = service._ai_skill_registry.create("workflow_capability_tagging")
    ai_capabilities = service._workflow_capability_tagging_skill.run(
        WorkflowCapabilityTaggingRequest(
            process_title=process_title,
            workflow_summary=workflow_summary,
            document_type=document_type,
        )
    )
    if ai_capabilities is not None and ai_capabilities.confidence in service._ACCEPTED_AI_CONFIDENCE and ai_capabilities.capability_tags:
        normalized_tags = service._normalize_capability_tags(ai_capabilities.capability_tags, process_title=process_title)
        if normalized_tags:
            return normalized_tags
    fallback_tags = service._fallback_capability_tags(workflow_profiles=workflow_profiles)
    return fallback_tags if fallback_tags else [process_title]
