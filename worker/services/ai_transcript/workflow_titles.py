from __future__ import annotations

import json
from typing import Any

from worker.services.ai_transcript.client import extract_content, parse_json_object, post_chat_completion
from worker.services.ai_transcript.models import WorkflowGroupMatchInterpretation, WorkflowTitleInterpretation
from worker.services.ai_transcript.normalization import (
    calibrate_confidence,
    normalize_confidence,
    normalize_existing_title,
    normalize_label,
    normalize_slug,
    title_quality_points,
    workflow_evidence_points,
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


def resolve_workflow_title(*, settings: Any, transcript_name: str, workflow_summary: dict[str, Any]) -> WorkflowTitleInterpretation | None:
    payload = {
        "model": settings.ai_model,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You normalize workflow evidence into a concise business workflow title. "
                    "Return strict JSON with keys: workflow_title, canonical_slug, confidence, rationale. "
                    "workflow_title must be a concise business noun phrase such as Sales Order Creation. "
                    "Prefer the stable operational workflow identity over raw UI phrasing. "
                    "Use the business object, workflow goal, system context, and repeated action pattern to infer the title. "
                    "Avoid UI action labels like Open, Go To, Click, Navigate, Select, or Enter as the leading verb. "
                    "Do not use a broad domain label such as Legal Analysis or Procurement unless the evidence does not support a more specific operational workflow title. "
                    "Use tool names only when the tool materially defines a different operational workflow identity. "
                    "canonical_slug must be lowercase kebab-case. "
                    "confidence must be one of high, medium, low, unknown."
                ),
            },
            {"role": "user", "content": json.dumps({"transcript_name": transcript_name, "workflow_summary": workflow_summary}, ensure_ascii=False)},
        ],
    }
    parsed = parse_json_object(extract_content(_post_json(settings=settings, payload=payload, context="workflow title resolution")))
    workflow_title = normalize_label(str(parsed.get("workflow_title", "") or ""))
    if not workflow_title:
        return None
    confidence = calibrate_confidence(
        normalize_confidence(parsed.get("confidence")),
        evidence_points=workflow_evidence_points(workflow_summary),
        quality_points=title_quality_points(workflow_title),
    )
    return WorkflowTitleInterpretation(
        workflow_title=workflow_title,
        canonical_slug=normalize_slug(str(parsed.get("canonical_slug", "") or ""), fallback=workflow_title),
        confidence=confidence,
        rationale=str(parsed.get("rationale", "") or "").strip(),
    )


def match_existing_workflow_group(
    *,
    settings: Any,
    transcript_name: str,
    workflow_summary: dict[str, Any],
    existing_groups: list[dict[str, Any]],
) -> WorkflowGroupMatchInterpretation | None:
    payload = {
        "model": settings.ai_model,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You decide whether new transcript-derived workflow evidence matches an existing workflow group. "
                    "Return strict JSON with keys: matched_existing_title, recommended_title, recommended_slug, confidence, rationale. "
                    "matched_existing_title must be either one exact title from existing_group_titles or an empty string. "
                    "recommended_title must be the workflow title that should be used. "
                    "recommended_slug must be lowercase kebab-case. "
                    "confidence must be one of high, medium, low, unknown. "
                    "Only choose an existing workflow when the operational workflow is materially the same. "
                    "Do not merge workflows only because they belong to the same business domain or professional function. "
                    "Different tools, different application contexts, or materially different interaction sequences should usually remain separate workflows. "
                    "Operational sameness should be evaluated using system context, business object flow, entry point, repeated action pattern, and outcome. "
                    "If only broad domain overlap exists, prefer creating a separate workflow and lower confidence."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "transcript_name": transcript_name,
                        "workflow_summary": workflow_summary,
                        "existing_group_titles": [group.get("title", "") for group in existing_groups],
                        "existing_groups": existing_groups,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
    }
    parsed = parse_json_object(extract_content(_post_json(settings=settings, payload=payload, context="workflow group matching")))
    recommended_title = normalize_label(str(parsed.get("recommended_title", "") or ""))
    if not recommended_title:
        return None
    confidence = calibrate_confidence(
        normalize_confidence(parsed.get("confidence")),
        evidence_points=workflow_evidence_points(workflow_summary),
        quality_points=2 if recommended_title else 0,
        lower_when=min(3, max(len(existing_groups) - 1, 0)),
    )
    return WorkflowGroupMatchInterpretation(
        matched_existing_title=normalize_existing_title(
            str(parsed.get("matched_existing_title", "") or ""),
            existing_titles=[str(group.get("title", "") or "") for group in existing_groups],
        ),
        recommended_title=recommended_title,
        recommended_slug=normalize_slug(str(parsed.get("recommended_slug", "") or ""), fallback=recommended_title),
        confidence=confidence,
        rationale=str(parsed.get("rationale", "") or "").strip(),
    )
