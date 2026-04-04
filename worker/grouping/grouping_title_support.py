from __future__ import annotations

import re
from typing import Callable

from app.models.artifact import ArtifactModel
from worker.pipeline.types import StepRecord
from worker.grouping.grouping_models import TranscriptWorkflowProfile
from worker.grouping.grouping_workflow_summary import signature_tokens

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


def starts_with_non_business_action(title: str) -> bool:
    lowered = title.lower().strip()
    return any(lowered.startswith(f"{action} ") or lowered == action for action in NON_BUSINESS_ACTIONS)


def _default_extract_leading_action_verb(action_text: str) -> str:
    match = re.match(r"^\s*([a-z]+(?:\s+[a-z]+)?)", action_text.lower())
    return match.group(1).strip() if match else ""


def normalize_workflow_title(
    *,
    base_title: str,
    steps: list[StepRecord],
    workflow_profile: TranscriptWorkflowProfile,
    extract_leading_action_verb: Callable[[str], str] = _default_extract_leading_action_verb,
) -> str:
    normalized_title = re.sub(r"\s+", " ", (base_title or "").strip()).title()
    object_name = workflow_profile.top_objects[0].title() if workflow_profile.top_objects else ""
    preferred_suffix = preferred_workflow_suffix(
        steps=steps,
        workflow_profile=workflow_profile,
        extract_leading_action_verb=extract_leading_action_verb,
    )
    if object_name:
        if preferred_suffix and not normalized_title.endswith(preferred_suffix):
            if starts_with_non_business_action(normalized_title):
                return f"{object_name} {preferred_suffix}".strip()
            if object_name.lower() in normalized_title.lower():
                return f"{object_name} {preferred_suffix}".strip()
        if starts_with_non_business_action(normalized_title):
            return f"{object_name} {preferred_suffix or 'Process'}".strip()
    if preferred_suffix and normalized_title and not normalized_title.endswith(preferred_suffix):
        if starts_with_non_business_action(normalized_title):
            return f"{normalized_title.split()[-1].title()} {preferred_suffix}".strip()
    return normalized_title or "Process"


def preferred_workflow_suffix(*, steps: list[StepRecord], workflow_profile: TranscriptWorkflowProfile, extract_leading_action_verb) -> str:  # type: ignore[no-untyped-def]
    action_candidates = [*workflow_profile.top_actions]
    action_candidates.extend(extract_leading_action_verb(str(step.get("action_text", "") or "")) for step in steps[:8])
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


def fallback_title(
    *,
    transcript: ArtifactModel,
    steps: list[StepRecord],
    workflow_profile: TranscriptWorkflowProfile,
    normalize_text,
    extract_leading_action_verb,
) -> str:  # type: ignore[no-untyped-def]
    if workflow_profile.top_goals:
        normalized_goal_title = normalize_workflow_title(
            base_title=workflow_profile.top_goals[0],
            steps=steps,
            workflow_profile=workflow_profile,
            extract_leading_action_verb=extract_leading_action_verb,
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
            extract_leading_action_verb=extract_leading_action_verb,
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
                extract_leading_action_verb=extract_leading_action_verb,
            )
    signature = list(signature_tokens(steps))
    if signature:
        phrase = " ".join(signature[:3]).strip()
        if phrase:
            normalized_signature_title = normalize_workflow_title(
                base_title=phrase.title(),
                steps=steps,
                workflow_profile=workflow_profile,
                extract_leading_action_verb=extract_leading_action_verb,
            )
            if normalized_signature_title:
                return normalized_signature_title
    transcript_title = transcript.name.rsplit(".", 1)[0].strip() or "Process"
    return normalize_workflow_title(
        base_title=transcript_title,
        steps=steps,
        workflow_profile=workflow_profile,
        extract_leading_action_verb=extract_leading_action_verb,
    )
