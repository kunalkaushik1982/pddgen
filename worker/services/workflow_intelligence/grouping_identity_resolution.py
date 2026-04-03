from __future__ import annotations

from collections.abc import Callable, Sequence
from difflib import SequenceMatcher

from app.models.process_group import ProcessGroupModel
from worker.services.ai_transcript_interpreter import WorkflowGroupMatchInterpretation
from worker.services.generation_types import StepRecord
from worker.services.workflow_intelligence.grouping_models import (
    CandidateMatchRecord,
    GroupResolutionDecision,
    HeuristicGroupMatchResult,
    TranscriptWorkflowProfile,
)
from worker.services.workflow_intelligence.grouping_title_resolution import STOPWORDS, normalize_text, signature_tokens, slugify


def heuristic_resolution_confidence(heuristic_match: HeuristicGroupMatchResult) -> str:
    best_score = float(heuristic_match["best_score"])
    matched_group = heuristic_match["matched_group"]
    ambiguity = bool(heuristic_match["ambiguity"])
    if ambiguity:
        return "medium"
    if matched_group is not None:
        return "high" if best_score >= 0.9 else "medium"
    return "high" if best_score < 0.55 else "medium"


def system_alignment_score(workflow_profile: TranscriptWorkflowProfile, group_tokens: set[str]) -> float:
    if not workflow_profile.top_systems:
        return 0.0
    normalized_systems = {normalize_text(value) for value in workflow_profile.top_systems if value}
    if not normalized_systems:
        return 0.0
    if any(system in " ".join(group_tokens) for system in normalized_systems):
        return 1.0
    return -0.5


def application_alignment_score(workflow_profile: TranscriptWorkflowProfile, group_tokens: set[str]) -> float:
    if not workflow_profile.top_applications:
        return 0.0
    normalized_applications = {normalize_text(value) for value in workflow_profile.top_applications if value}
    if not normalized_applications:
        return 0.0
    if any(application in " ".join(group_tokens) for application in normalized_applications):
        return 1.0
    return -0.75


def has_explicit_tool_mismatch(workflow_profile: TranscriptWorkflowProfile, group_tokens: set[str]) -> bool:
    tool_markers = [normalize_text(value) for value in [*workflow_profile.top_systems, *workflow_profile.top_applications] if value]
    if len(tool_markers) == 0:
        return False
    normalized_group_text = " ".join(group_tokens)
    return all(marker not in normalized_group_text for marker in tool_markers)


def profile_tokens(profile: TranscriptWorkflowProfile) -> set[str]:
    parts = [
        *profile.top_actors,
        *profile.top_objects,
        *profile.top_systems,
        *profile.top_applications,
        *profile.top_actions,
        *profile.top_goals,
        *profile.top_rules,
        *profile.top_domain_terms,
    ]
    normalized = normalize_text(" ".join(parts))
    return {token for token in normalized.split() if token and token not in STOPWORDS}


def match_existing_group(
    *,
    slug: str,
    title: str,
    steps: Sequence[StepRecord],
    workflow_profile: TranscriptWorkflowProfile,
    existing_groups: Sequence[ProcessGroupModel],
) -> HeuristicGroupMatchResult:
    for group in existing_groups:
        if slug and group.canonical_slug == slug:
            return {
                "matched_group": group,
                "best_score": 1.0,
                "ambiguity": False,
                "candidate_matches": [{"group_title": group.title, "score": 1.0}],
                "supporting_signals": ["canonical_slug_match"],
            }

    normalized_title = normalize_text(title)
    candidate_signature = signature_tokens(steps)
    workflow_profile_tokens = profile_tokens(workflow_profile)
    best_group: ProcessGroupModel | None = None
    best_score = 0.0
    second_best_score = 0.0
    candidate_scores: list[CandidateMatchRecord] = []
    for group in existing_groups:
        title_ratio = SequenceMatcher(None, normalized_title, normalize_text(group.title)).ratio()
        signature_overlap = 0.0
        system_alignment = 0.0
        application_alignment = 0.0
        group_tokens: set[str] = set()
        if getattr(group, "summary_text", ""):
            group_tokens = {token for token in normalize_text(group.summary_text).split() if token and token not in STOPWORDS}
            signature_overlap = len(candidate_signature & group_tokens) / max(len(candidate_signature | group_tokens), 1)
            profile_overlap = (
                len(workflow_profile_tokens & group_tokens) / max(len(workflow_profile_tokens | group_tokens), 1)
                if workflow_profile_tokens
                else 0.0
            )
            system_alignment = system_alignment_score(workflow_profile, group_tokens)
            application_alignment = application_alignment_score(workflow_profile, group_tokens)
        else:
            profile_overlap = 0.0
        score = (
            (title_ratio * 0.35)
            + (signature_overlap * 0.18)
            + (profile_overlap * 0.12)
            + (system_alignment * 0.15)
            + (application_alignment * 0.2)
        )
        if has_explicit_tool_mismatch(workflow_profile, group_tokens):
            score -= 0.25
        candidate_scores.append(
            {
                "group_title": group.title,
                "score": round(score, 3),
                "title_ratio": round(title_ratio, 3),
                "signature_overlap": round(signature_overlap, 3),
                "profile_overlap": round(profile_overlap, 3),
                "system_alignment": round(system_alignment, 3),
                "application_alignment": round(application_alignment, 3),
            }
        )
        if score > best_score:
            second_best_score = best_score
            best_score = score
            best_group = group
        elif score > second_best_score:
            second_best_score = score

    candidate_scores.sort(key=lambda item: float(item.get("score", 0.0) or 0.0), reverse=True)
    ambiguity = best_score >= 0.72 and second_best_score >= 0.7 and abs(best_score - second_best_score) <= 0.15
    supporting_signals: list[str] = []
    if best_score >= 0.82:
        supporting_signals.append("strong_existing_group_match")
    elif best_score >= 0.72:
        supporting_signals.append("moderate_existing_group_match")
    if ambiguity:
        supporting_signals.append("competing_group_candidates")

    return {
        "matched_group": best_group if best_score >= 0.86 else None,
        "best_score": best_score,
        "ambiguity": ambiguity,
        "candidate_matches": candidate_scores[:3],
        "supporting_signals": supporting_signals,
    }


def build_ai_group_match_decision(
    *,
    ai_match: WorkflowGroupMatchInterpretation,
    fallback_title: str,
    existing_groups: Sequence[ProcessGroupModel],
    decision_source: str,
    heuristic_decision: str | None,
    heuristic_confidence: str | None,
    ai_decision: str,
    ai_confidence: str,
    conflict_detected: bool,
    supporting_signals: list[str] | None = None,
    rationale_prefix: str = "",
) -> GroupResolutionDecision:
    matched_group = next((group for group in existing_groups if group.title == ai_match.matched_existing_title), None)
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
    resolved_heuristic_decision = heuristic_decision or ("matched_existing_group" if matched_group is not None else "created_new_group")
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


def serialize_existing_groups_for_ai(
    *,
    existing_groups: Sequence[ProcessGroupModel],
    heuristic_match: HeuristicGroupMatchResult,
    parse_capability_tags: Callable[[str], list[str]],
) -> list[dict[str, object]]:
    candidate_scores: dict[str, CandidateMatchRecord] = {
        str(item.get("group_title", "")): item
        for item in heuristic_match["candidate_matches"]
    }
    serialized: list[dict[str, object]] = []
    for group in existing_groups:
        candidate_score = candidate_scores.get(group.title)
        serialized.append(
            {
                "title": group.title,
                "canonical_slug": group.canonical_slug,
                "summary_text": getattr(group, "summary_text", "") or "",
                "capability_tags": parse_capability_tags(getattr(group, "capability_tags_json", "[]")),
                "summary_tokens": [
                    token
                    for token in normalize_text(getattr(group, "summary_text", "") or "").split()
                    if token and token not in STOPWORDS
                ][:10],
                "heuristic_score": candidate_score.get("score") if candidate_score is not None else None,
                "heuristic_title_ratio": candidate_score.get("title_ratio") if candidate_score is not None else None,
                "heuristic_signature_overlap": candidate_score.get("signature_overlap") if candidate_score is not None else None,
                "heuristic_system_alignment": candidate_score.get("system_alignment") if candidate_score is not None else None,
                "heuristic_application_alignment": candidate_score.get("application_alignment") if candidate_score is not None else None,
            }
        )
    return serialized


__all__ = [
    "application_alignment_score",
    "build_ai_group_match_decision",
    "build_heuristic_group_decision",
    "has_explicit_tool_mismatch",
    "heuristic_resolution_confidence",
    "match_existing_group",
    "profile_tokens",
    "serialize_existing_groups_for_ai",
    "system_alignment_score",
]
