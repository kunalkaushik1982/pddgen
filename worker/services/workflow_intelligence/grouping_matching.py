from __future__ import annotations

from difflib import SequenceMatcher
from typing import cast

from app.models.process_group import ProcessGroupModel
from worker.services.generation_types import StepRecord
from worker.services.workflow_intelligence.grouping_models import CandidateMatchRecord, HeuristicGroupMatchResult, TranscriptWorkflowProfile


def system_alignment_score(*, workflow_profile: TranscriptWorkflowProfile, group_tokens: set[str], normalize_text) -> float:  # type: ignore[no-untyped-def]
    if not workflow_profile.top_systems:
        return 0.0
    normalized_systems = {normalize_text(value) for value in workflow_profile.top_systems if value}
    if not normalized_systems:
        return 0.0
    if any(system in " ".join(group_tokens) for system in normalized_systems):
        return 1.0
    return -0.5


def application_alignment_score(*, workflow_profile: TranscriptWorkflowProfile, group_tokens: set[str], normalize_text) -> float:  # type: ignore[no-untyped-def]
    if not workflow_profile.top_applications:
        return 0.0
    normalized_applications = {normalize_text(value) for value in workflow_profile.top_applications if value}
    if not normalized_applications:
        return 0.0
    if any(application in " ".join(group_tokens) for application in normalized_applications):
        return 1.0
    return -0.75


def has_explicit_tool_mismatch(*, workflow_profile: TranscriptWorkflowProfile, group_tokens: set[str], normalize_text) -> bool:  # type: ignore[no-untyped-def]
    tool_markers = [normalize_text(value) for value in [*workflow_profile.top_systems, *workflow_profile.top_applications] if value]
    if len(tool_markers) == 0:
        return False
    normalized_group_text = " ".join(group_tokens)
    return all(marker not in normalized_group_text for marker in tool_markers)


def match_existing_group(
    *,
    slug: str,
    title: str,
    steps: list[StepRecord],
    workflow_profile: TranscriptWorkflowProfile,
    existing_groups: list[ProcessGroupModel],
    normalize_text,
    stopwords: set[str],
    signature_tokens,
) -> HeuristicGroupMatchResult:  # type: ignore[no-untyped-def]
    for group in existing_groups:
        if slug and group.canonical_slug == slug:
            return cast(HeuristicGroupMatchResult, {
                "matched_group": group,
                "best_score": 1.0,
                "ambiguity": False,
                "candidate_matches": [{"group_title": group.title, "score": 1.0}],
                "supporting_signals": ["canonical_slug_match"],
            })
    normalized_title = normalize_text(title)
    candidate_signature = signature_tokens(steps)
    profile_parts = [
        *workflow_profile.top_actors,
        *workflow_profile.top_objects,
        *workflow_profile.top_systems,
        *workflow_profile.top_applications,
        *workflow_profile.top_actions,
        *workflow_profile.top_goals,
        *workflow_profile.top_rules,
        *workflow_profile.top_domain_terms,
    ]
    profile_tokens = {token for token in normalize_text(" ".join(profile_parts)).split() if token and token not in stopwords}
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
            group_tokens = {token for token in normalize_text(group.summary_text).split() if token and token not in stopwords}
            signature_overlap = len(candidate_signature & group_tokens) / max(len(candidate_signature | group_tokens), 1)
            profile_overlap = len(profile_tokens & group_tokens) / max(len(profile_tokens | group_tokens), 1) if profile_tokens else 0.0
            system_alignment = system_alignment_score(workflow_profile=workflow_profile, group_tokens=group_tokens, normalize_text=normalize_text)
            application_alignment = application_alignment_score(workflow_profile=workflow_profile, group_tokens=group_tokens, normalize_text=normalize_text)
        else:
            profile_overlap = 0.0
        score = (
            (title_ratio * 0.35)
            + (signature_overlap * 0.18)
            + (profile_overlap * 0.12)
            + (system_alignment * 0.15)
            + (application_alignment * 0.2)
        )
        if has_explicit_tool_mismatch(workflow_profile=workflow_profile, group_tokens=group_tokens, normalize_text=normalize_text):
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
    supporting_signals = []
    if best_score >= 0.82:
        supporting_signals.append("strong_existing_group_match")
    elif best_score >= 0.72:
        supporting_signals.append("moderate_existing_group_match")
    if ambiguity:
        supporting_signals.append("competing_group_candidates")
    return cast(HeuristicGroupMatchResult, {
        "matched_group": best_group if best_score >= 0.86 else None,
        "best_score": best_score,
        "ambiguity": ambiguity,
        "candidate_matches": candidate_scores[:3],
        "supporting_signals": supporting_signals,
    })
