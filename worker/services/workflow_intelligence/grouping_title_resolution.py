from __future__ import annotations

import re
from collections.abc import Sequence
from typing import TYPE_CHECKING

from app.models.artifact import ArtifactModel
from worker.services.generation_types import NoteRecord, StepRecord

if TYPE_CHECKING:
    from worker.services.workflow_intelligence.grouping_models import TranscriptWorkflowProfile


WORKFLOW_SUFFIX_BY_ACTION = {
    "create": "Creation",
    "submit": "Creation",
    "save": "Creation",
    "update": "Maintenance",
    "edit": "Maintenance",
    "change": "Maintenance",
    "maintain": "Maintenance",
    "review": "Review",
    "approve": "Approval",
    "validate": "Validation",
    "check": "Validation",
    "reconcile": "Reconciliation",
    "post": "Posting",
}
NON_BUSINESS_ACTIONS = {
    "open",
    "go",
    "go to",
    "goto",
    "navigate",
    "launch",
    "login",
    "log in",
    "select",
    "click",
    "enter",
}
STOPWORDS = {
    "a",
    "an",
    "and",
    "the",
    "to",
    "of",
    "for",
    "in",
    "on",
    "with",
    "into",
    "from",
    "then",
    "after",
    "before",
    "click",
    "select",
    "enter",
    "open",
    "go",
    "navigate",
    "screen",
    "field",
    "data",
    "details",
    "form",
    "tab",
    "save",
    "submit",
    "create",
    "creation",
    "process",
}


def normalize_text(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9\s]+", " ", value.lower())
    return re.sub(r"\s+", " ", normalized).strip()


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9\s-]+", " ", value.lower())
    collapsed = re.sub(r"\s+", "-", normalized.strip())
    return re.sub(r"-{2,}", "-", collapsed).strip("-") or "process"


def starts_with_non_business_action(title: str) -> bool:
    lowered = title.lower().strip()
    return any(lowered.startswith(f"{action} ") or lowered == action for action in NON_BUSINESS_ACTIONS)


def extract_leading_action_verb(action_text: str) -> str:
    match = re.match(r"^\s*([a-z]+(?:\s+[a-z]+)?)", action_text.lower())
    return match.group(1).strip() if match else ""


def preferred_workflow_suffix(*, steps: Sequence[StepRecord], workflow_profile: TranscriptWorkflowProfile) -> str:
    action_candidates = [*workflow_profile.top_actions]
    action_candidates.extend(
        extract_leading_action_verb(str(step.get("action_text", "") or ""))
        for step in steps[:8]
    )
    for action in action_candidates:
        if not action:
            continue
        normalized_action = action.lower().strip()
        if normalized_action in NON_BUSINESS_ACTIONS:
            continue
        suffix = WORKFLOW_SUFFIX_BY_ACTION.get(normalized_action)
        if suffix:
            return suffix
    return "Creation" if workflow_profile.top_objects else "Process"


def normalize_workflow_title(
    *,
    base_title: str,
    steps: Sequence[StepRecord],
    workflow_profile: TranscriptWorkflowProfile,
) -> str:
    normalized_title = re.sub(r"\s+", " ", (base_title or "").strip()).title()
    object_name = workflow_profile.top_objects[0].title() if workflow_profile.top_objects else ""
    suffix = preferred_workflow_suffix(steps=steps, workflow_profile=workflow_profile)

    if object_name:
        if suffix and not normalized_title.endswith(suffix):
            if starts_with_non_business_action(normalized_title):
                return f"{object_name} {suffix}".strip()
            if object_name.lower() in normalized_title.lower():
                return f"{object_name} {suffix}".strip()
        if starts_with_non_business_action(normalized_title):
            return f"{object_name} {suffix or 'Process'}".strip()

    if suffix and normalized_title and not normalized_title.endswith(suffix):
        if starts_with_non_business_action(normalized_title):
            return f"{normalized_title.split()[-1].title()} {suffix}".strip()

    return normalized_title or "Process"


def signature_tokens(steps: Sequence[StepRecord]) -> set[str]:
    text = " ".join(str(step.get("action_text", "") or "") for step in steps[:12])
    tokens = [token for token in normalize_text(text).split() if token and token not in STOPWORDS]
    counts: dict[str, int] = {}
    for token in tokens:
        counts[token] = counts.get(token, 0) + 1
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return {token for token, _ in ordered[:5]}


def operation_signature_from_steps(steps: Sequence[StepRecord]) -> list[str]:
    signature: list[str] = []
    seen: set[str] = set()
    for step in steps[:8]:
        action_text = str(step.get("action_text", "") or "").strip()
        if not action_text:
            continue
        normalized = normalize_text(action_text)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        signature.append(action_text)
        if len(signature) >= 5:
            break
    return signature


def fallback_title(*, transcript: ArtifactModel, steps: Sequence[StepRecord], workflow_profile: TranscriptWorkflowProfile) -> str:
    if workflow_profile.top_goals:
        normalized_goal_title = normalize_workflow_title(
            base_title=workflow_profile.top_goals[0],
            steps=steps,
            workflow_profile=workflow_profile,
        )
        if normalized_goal_title:
            return normalized_goal_title
    if workflow_profile.top_objects:
        object_name = workflow_profile.top_objects[0]
        action_name = workflow_profile.top_actions[0] if workflow_profile.top_actions else None
        normalized_object_title = normalize_workflow_title(
            base_title=f"{object_name} {action_name}".strip() if action_name else object_name,
            steps=steps,
            workflow_profile=workflow_profile,
        )
        if normalized_object_title:
            return normalized_object_title

    combined = " ".join(
        [
            transcript.name,
            *[str(step.get("action_text", "") or "") for step in steps[:8]],
            *[str(step.get("supporting_transcript_text", "") or "") for step in steps[:3]],
        ]
    )
    normalized = normalize_text(combined)

    explicit_patterns = [
        r"\b(sales order(?: creation)?)\b",
        r"\b(purchase order(?: creation)?)\b",
        r"\b(goods receipt)\b",
        r"\b(invoice(?: creation| posting)?)\b",
    ]
    for pattern in explicit_patterns:
        match = re.search(pattern, normalized)
        if match:
            return normalize_workflow_title(
                base_title=match.group(1).title(),
                steps=steps,
                workflow_profile=workflow_profile,
            )

    signature = list(signature_tokens(steps))
    if signature:
        phrase = " ".join(signature[:3]).strip()
        if phrase:
            normalized_signature_title = normalize_workflow_title(
                base_title=phrase.title(),
                steps=steps,
                workflow_profile=workflow_profile,
            )
            if normalized_signature_title:
                return normalized_signature_title
    transcript_title = transcript.name.rsplit(".", 1)[0].strip() or "Process"
    return normalize_workflow_title(
        base_title=transcript_title,
        steps=steps,
        workflow_profile=workflow_profile,
    )


def group_summary_seed(
    *,
    inferred_title: str,
    steps: Sequence[StepRecord],
    notes: Sequence[NoteRecord],
    workflow_profile: TranscriptWorkflowProfile,
) -> str:
    parts = [inferred_title]
    parts.extend(workflow_profile.top_actors[:2])
    parts.extend(workflow_profile.top_goals[:2])
    parts.extend(workflow_profile.top_objects[:2])
    parts.extend(workflow_profile.top_systems[:2])
    parts.extend(workflow_profile.top_rules[:2])
    parts.extend(str(step.get("action_text", "") or "") for step in steps[:6])
    parts.extend(str(note.get("text", "") or "") for note in notes[:3])
    return " ".join(part for part in parts if part).strip()


__all__ = [
    "STOPWORDS",
    "extract_leading_action_verb",
    "fallback_title",
    "group_summary_seed",
    "normalize_text",
    "normalize_workflow_title",
    "operation_signature_from_steps",
    "preferred_workflow_suffix",
    "signature_tokens",
    "slugify",
    "starts_with_non_business_action",
]
