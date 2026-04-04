from __future__ import annotations

import json
from typing import Any

from worker.services.ai_transcript.client import extract_content, parse_json_object
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
from worker.services.ai_transcript.workflow_prompts import WORKFLOW_GROUP_MATCH_PROMPT, WORKFLOW_TITLE_PROMPT
from worker.services.ai_transcript.workflow_runtime import post_json


def resolve_workflow_title(*, settings: Any, transcript_name: str, workflow_summary: dict[str, Any]) -> WorkflowTitleInterpretation | None:
    payload = {
        "model": settings.ai_model,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": WORKFLOW_TITLE_PROMPT},
            {"role": "user", "content": json.dumps({"transcript_name": transcript_name, "workflow_summary": workflow_summary}, ensure_ascii=False)},
        ],
    }
    parsed = parse_json_object(extract_content(post_json(settings=settings, payload=payload, context="workflow title resolution")))
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
            {"role": "system", "content": WORKFLOW_GROUP_MATCH_PROMPT},
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
    parsed = parse_json_object(extract_content(post_json(settings=settings, payload=payload, context="workflow group matching")))
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
