from __future__ import annotations

from collections.abc import Callable

from app.models.artifact import ArtifactModel
from app.models.process_group import ProcessGroupModel
from worker.ai_skills.transcript_interpreter.interpreter import AmbiguousProcessGroupResolution
from worker.ai_skills.transcript_interpreter.interpreter import WorkflowGroupMatchInterpretation
from worker.grouping.grouping_models import (
    CandidateMatchRecord,
    GroupResolutionDecision,
    HeuristicGroupMatchResult,
)


def heuristic_resolution_confidence(heuristic_match: HeuristicGroupMatchResult) -> str:
    best_score = float(heuristic_match["best_score"])
    matched_group = heuristic_match["matched_group"]
    ambiguity = bool(heuristic_match["ambiguity"])
    if ambiguity:
        return "medium"
    if matched_group is not None:
        return "high" if best_score >= 0.9 else "medium"
    return "high" if best_score < 0.55 else "medium"


def build_ai_group_match_decision(
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
    slugify: Callable[[str], str],
    supporting_signals: list[str] | None = None,
    rationale_prefix: str = "",
) -> GroupResolutionDecision:
    matched_group = next(
        (group for group in existing_groups if group.title == ai_match.matched_existing_title),
        None,
    )
    resolved_title = ai_match.recommended_title.strip() or fallback_title
    resolved_slug = slugify(ai_match.recommended_slug or resolved_title)
    rationale = ai_match.rationale or (
        f"AI matched this transcript to existing workflow '{matched_group.title}'."
        if matched_group is not None
        else f"AI determined this transcript should create workflow '{resolved_title}'."
    )
    if rationale_prefix:
        rationale = f"{rationale_prefix} {rationale}".strip()
    if matched_group is not None:
        return GroupResolutionDecision(
            inferred_title=resolved_title,
            inferred_slug=resolved_slug,
            matched_group=matched_group,
            decision="ai_matched_existing_group",
            confidence=ai_match.confidence,
            decision_source=decision_source,
            is_ambiguous=False,
            rationale=rationale,
            candidate_matches=[{"group_title": matched_group.title, "score": ai_match.confidence}],
            supporting_signals=supporting_signals or ["ai_group_matcher"],
            heuristic_decision=heuristic_decision,
            heuristic_confidence=heuristic_confidence,
            ai_decision=ai_decision,
            ai_confidence=ai_confidence,
            conflict_detected=conflict_detected,
        )
    return GroupResolutionDecision(
        inferred_title=resolved_title,
        inferred_slug=resolved_slug,
        matched_group=None,
        decision="ai_created_new_group",
        confidence=ai_match.confidence,
        decision_source=decision_source,
        is_ambiguous=False,
        rationale=rationale,
        candidate_matches=[],
        supporting_signals=supporting_signals or ["ai_group_matcher"],
        heuristic_decision=heuristic_decision,
        heuristic_confidence=heuristic_confidence,
        ai_decision=ai_decision,
        ai_confidence=ai_confidence,
        conflict_detected=conflict_detected,
    )


def build_heuristic_group_decision(
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
) -> GroupResolutionDecision:
    matched_group = heuristic_match["matched_group"]
    ambiguity = bool(heuristic_match["ambiguity"]) or force_ambiguous
    candidate_matches = list(heuristic_match["candidate_matches"])
    supporting_signals = [
        *title_supporting_signals,
        *list(heuristic_match["supporting_signals"]),
        *(extra_supporting_signals or []),
    ]
    resolved_heuristic_decision = heuristic_decision or (
        "matched_existing_group" if matched_group is not None else "created_new_group"
    )
    resolved_heuristic_confidence = heuristic_confidence or heuristic_resolution_confidence(heuristic_match)
    if matched_group is not None:
        return GroupResolutionDecision(
            inferred_title=inferred_title,
            inferred_slug=inferred_slug,
            matched_group=matched_group,
            decision="matched_existing_group" if not ambiguity else "ambiguously_matched_existing_group",
            confidence=resolved_heuristic_confidence,
            decision_source=decision_source,
            is_ambiguous=ambiguity,
            rationale=(
                rationale_override
                or (
                    f"Matched to existing workflow '{matched_group.title}' using title and profile overlap."
                    if not ambiguity
                    else f"Matched to existing workflow '{matched_group.title}', but another plausible workflow also scored closely."
                )
            ),
            candidate_matches=candidate_matches,
            supporting_signals=supporting_signals,
            heuristic_decision=resolved_heuristic_decision,
            heuristic_confidence=resolved_heuristic_confidence,
            ai_decision=ai_decision,
            ai_confidence=ai_confidence,
            conflict_detected=conflict_detected,
        )
    return GroupResolutionDecision(
        inferred_title=inferred_title,
        inferred_slug=inferred_slug,
        matched_group=None,
        decision="created_new_group" if not ambiguity else "ambiguously_created_new_group",
        confidence="medium" if ambiguity else resolved_heuristic_confidence,
        decision_source=decision_source,
        is_ambiguous=ambiguity,
        rationale=(
            rationale_override
            or (
                f"No strong existing workflow match was found for inferred workflow '{inferred_title}'."
                if not ambiguity
                else f"No confident workflow match was found for inferred workflow '{inferred_title}', so a new group was created conservatively."
            )
        ),
        candidate_matches=candidate_matches,
        supporting_signals=supporting_signals,
        heuristic_decision=resolved_heuristic_decision,
        heuristic_confidence=resolved_heuristic_confidence,
        ai_decision=ai_decision,
        ai_confidence=ai_confidence,
        conflict_detected=conflict_detected,
    )


def resolve_ambiguity_with_ai(
    *,
    ai_resolution: AmbiguousProcessGroupResolution | None,
    inferred_title: str,
    candidate_matches: list[CandidateMatchRecord],
    existing_groups: list[ProcessGroupModel],
    slugify: Callable[[str], str],
) -> GroupResolutionDecision | None:
    if ai_resolution is None or ai_resolution.confidence != "high":
        return None

    matched_group = next(
        (group for group in existing_groups if group.title == ai_resolution.matched_existing_title),
        None,
    )
    resolved_title = ai_resolution.recommended_title.strip() or inferred_title
    resolved_slug = slugify(ai_resolution.recommended_slug or resolved_title)
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
