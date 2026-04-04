from __future__ import annotations

import json
from typing import Any

from worker.ai_skills.transcript_interpreter.client import extract_content, parse_json_object
from worker.ai_skills.transcript_interpreter.models import WorkflowBoundaryInterpretation, WorkflowSemanticEnrichmentInterpretation
from worker.ai_skills.transcript_interpreter.normalization import (
    calibrate_confidence,
    normalize_confidence,
    normalize_label_list,
    normalize_optional_text,
)
from worker.ai_skills.transcript_interpreter.workflow_prompts import WORKFLOW_BOUNDARY_PROMPT, WORKFLOW_ENRICHMENT_PROMPT
from worker.ai_skills.transcript_interpreter.workflow_runtime import post_json


def classify_workflow_boundary(*, settings: Any, left_segment: dict[str, Any], right_segment: dict[str, Any]) -> WorkflowBoundaryInterpretation | None:
    payload = {
        "model": settings.ai_model,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": WORKFLOW_BOUNDARY_PROMPT},
            {"role": "user", "content": json.dumps({"left_segment": left_segment, "right_segment": right_segment}, ensure_ascii=False)},
        ],
    }
    parsed = parse_json_object(
        extract_content(post_json(settings=settings, payload=payload, context="workflow boundary classification"))
    )
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
            {"role": "system", "content": WORKFLOW_ENRICHMENT_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {"transcript_name": transcript_name or "", "segment_context": segment_context or {}, "segment_text": segment_text},
                    ensure_ascii=False,
                ),
            },
        ],
    }
    parsed = parse_json_object(
        extract_content(post_json(settings=settings, payload=payload, context="workflow semantic enrichment"))
    )
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
