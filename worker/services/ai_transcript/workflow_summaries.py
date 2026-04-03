from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from worker.services.ai_transcript.client import extract_content, parse_json_object, post_chat_completion
from worker.services.ai_transcript.models import ProcessSummaryInterpretation, WorkflowCapabilityInterpretation
from worker.services.ai_transcript.normalization import (
    calibrate_confidence,
    normalize_confidence,
    normalize_label_list,
    summary_quality_points,
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


def summarize_process_group(
    *,
    settings: Any,
    process_title: str,
    workflow_summary: dict[str, Any],
    steps: Sequence[Mapping[str, Any]],
    notes: Sequence[Mapping[str, Any]],
    document_type: str,
) -> ProcessSummaryInterpretation | None:
    payload = {
        "model": settings.ai_model,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You generate a concise business summary for one resolved workflow group. "
                    "Return strict JSON with keys: summary_text, confidence, rationale. "
                    "summary_text must be 2 to 4 plain-English sentences that describe the workflow purpose, the main business actions, "
                    "and the business outcome. "
                    "Do not produce bullet points. "
                    "Do not zigzag across unrelated workflows. "
                    "Keep the summary scoped only to the provided workflow evidence. "
                    "Use business language instead of UI click-by-click language when possible. "
                    "Prefer the operational workflow identity and business outcome over raw transcript wording. "
                    "confidence must be one of high, medium, low, unknown."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "document_type": document_type,
                        "process_title": process_title,
                        "workflow_summary": workflow_summary,
                        "steps": [
                            {
                                "application_name": step.get("application_name", ""),
                                "action_text": step.get("action_text", ""),
                                "supporting_transcript_text": step.get("supporting_transcript_text", ""),
                            }
                            for step in steps[:12]
                        ],
                        "notes": [
                            {
                                "text": note.get("text", ""),
                                "inference_type": note.get("inference_type", ""),
                            }
                            for note in notes[:6]
                        ],
                    },
                    ensure_ascii=False,
                ),
            },
        ],
    }
    parsed = parse_json_object(extract_content(_post_json(settings=settings, payload=payload, context="process summary generation")))
    summary_text = str(parsed.get("summary_text", "") or "").strip()
    if not summary_text:
        return None
    confidence = calibrate_confidence(
        normalize_confidence(parsed.get("confidence")),
        evidence_points=workflow_evidence_points(workflow_summary),
        quality_points=summary_quality_points(summary_text),
    )
    return ProcessSummaryInterpretation(
        summary_text=summary_text,
        confidence=confidence,
        rationale=str(parsed.get("rationale", "") or "").strip(),
    )


def classify_workflow_capabilities(
    *,
    settings: Any,
    process_title: str,
    workflow_summary: dict[str, Any],
    document_type: str,
) -> WorkflowCapabilityInterpretation | None:
    payload = {
        "model": settings.ai_model,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You classify broader business capability tags for one workflow. "
                    "Return strict JSON with keys: capability_tags, confidence, rationale. "
                    "capability_tags must be a short list of 1 to 3 business capability labels such as Contract Review, Legal Document Analysis, Sales Operations, or Procurement. "
                    "These tags describe broad business capability and must not redefine workflow identity. "
                    "Do not return tool names, exact workflow titles, or low-value generic labels. "
                    "Prefer reusable cross-tool business capability labels. "
                    "confidence must be one of high, medium, low, unknown."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {"document_type": document_type, "process_title": process_title, "workflow_summary": workflow_summary},
                    ensure_ascii=False,
                ),
            },
        ],
    }
    parsed = parse_json_object(
        extract_content(_post_json(settings=settings, payload=payload, context="workflow capability classification"))
    )
    capability_tags = normalize_label_list(parsed.get("capability_tags", []), max_items=3, exclude={process_title})
    confidence = calibrate_confidence(
        normalize_confidence(parsed.get("confidence")),
        evidence_points=workflow_evidence_points(workflow_summary),
        quality_points=len(capability_tags),
    )
    return WorkflowCapabilityInterpretation(
        capability_tags=capability_tags,
        confidence=confidence,
        rationale=str(parsed.get("rationale", "") or "").strip(),
    )
