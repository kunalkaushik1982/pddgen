from __future__ import annotations

import json
from typing import Any

from worker.services.ai_transcript.client import extract_content, parse_json_object, post_chat_completion
from worker.services.ai_transcript.models import WorkflowBoundaryInterpretation, WorkflowSemanticEnrichmentInterpretation
from worker.services.ai_transcript.normalization import (
    calibrate_confidence,
    normalize_confidence,
    normalize_label_list,
    normalize_optional_text,
)


def _post_json(*, settings: Any, payload: dict[str, Any], context: str) -> dict[str, Any]:
    endpoint = f"{settings.ai_base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.ai_api_key}",
        "Content-Type": "application/json",
    }
    return post_chat_completion(
        timeout_seconds=settings.ai_timeout_seconds,
        endpoint=endpoint,
        headers=headers,
        payload=payload,
        context=context,
    )


def _post_and_extract(*, settings: Any, payload: dict[str, Any], context: str) -> dict[str, Any]:
    return parse_json_object(extract_content(_post_json(settings=settings, payload=payload, context=context)))


def classify_workflow_boundary(
    *,
    settings: Any,
    left_segment: dict[str, Any],
    right_segment: dict[str, Any],
) -> WorkflowBoundaryInterpretation | None:
    payload = {
        "model": settings.ai_model,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You classify whether two adjacent evidence segments belong to the same business workflow. "
                    "Return strict JSON with keys: decision, confidence, rationale. "
                    "decision must be one of same_workflow, new_workflow, uncertain. "
                    "confidence must be one of high, medium, low, unknown. "
                    "Use the workflow goal, business object, actor, system, action type, domain terms, rule hints, and transcript wording. "
                    "Prefer same_workflow only when the business workflow clearly continues. "
                    "Prefer new_workflow when the adjacent segment appears to start a materially different business activity. "
                    "Use uncertain when the evidence conflicts or remains genuinely ambiguous."
                ),
            },
            {"role": "user", "content": json.dumps({"left_segment": left_segment, "right_segment": right_segment}, ensure_ascii=False)},
        ],
    }
    parsed = _post_and_extract(settings=settings, payload=payload, context="workflow boundary classification")
    decision = str(parsed.get("decision", "") or "").strip().lower()
    if decision not in {"same_workflow", "new_workflow", "uncertain"}:
        return None
    return WorkflowBoundaryInterpretation(
        decision=decision,
        confidence=normalize_confidence(parsed.get("confidence")),
        rationale=str(parsed.get("rationale", "") or "").strip(),
    )


def enrich_workflow_segment(
    *,
    settings: Any,
    segment_text: str,
    transcript_name: str | None = None,
    segment_context: dict[str, Any] | None = None,
) -> WorkflowSemanticEnrichmentInterpretation | None:
    payload = {
        "model": settings.ai_model,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You enrich one workflow evidence segment with business workflow labels. "
                    "Return strict JSON with keys: actor, actor_role, system_name, action_verb, action_type, "
                    "business_object, workflow_goal, rule_hints, domain_terms, confidence, rationale. "
                    "actor_role should be a concise role like operator, approver, reviewer, external_party, or system. "
                    "action_type should be a concise business action category such as navigate, create, update, review, approve, validate, extract, or submit. "
                    "workflow_goal should be a concise business goal phrase, not a raw UI action. "
                    "rule_hints and domain_terms must be arrays. "
                    "Prefer operationally meaningful labels over generic domain labels. "
                    "Use null for unknown scalar fields rather than guessing. "
                    "confidence must be one of high, medium, low, unknown. "
                    "Lower confidence when the segment does not contain enough evidence to support a precise operational interpretation."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "transcript_name": transcript_name or "",
                        "segment_context": segment_context or {},
                        "segment_text": segment_text,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
    }
    parsed = _post_and_extract(settings=settings, payload=payload, context="workflow semantic enrichment")
    domain_terms = normalize_label_list(parsed.get("domain_terms", []), max_items=6)
    rule_hints = normalize_label_list(parsed.get("rule_hints", []), max_items=4)
    filled_fields = sum(
        1
        for value in (
            parsed.get("actor"),
            parsed.get("actor_role"),
            parsed.get("system_name"),
            parsed.get("action_verb"),
            parsed.get("action_type"),
            parsed.get("business_object"),
            parsed.get("workflow_goal"),
        )
        if normalize_optional_text(value)
    )
    confidence = calibrate_confidence(
        normalize_confidence(parsed.get("confidence")),
        evidence_points=filled_fields,
        quality_points=len(domain_terms) + len(rule_hints),
    )
    return WorkflowSemanticEnrichmentInterpretation(
        actor=normalize_optional_text(parsed.get("actor")),
        actor_role=normalize_optional_text(parsed.get("actor_role")),
        system_name=normalize_optional_text(parsed.get("system_name")),
        action_verb=normalize_optional_text(parsed.get("action_verb")),
        action_type=normalize_optional_text(parsed.get("action_type")),
        business_object=normalize_optional_text(parsed.get("business_object")),
        workflow_goal=normalize_optional_text(parsed.get("workflow_goal")),
        rule_hints=rule_hints,
        domain_terms=domain_terms,
        confidence=confidence,
        rationale=str(parsed.get("rationale", "") or "").strip(),
    )
