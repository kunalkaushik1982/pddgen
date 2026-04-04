from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from worker.ai_skills.transcript_interpreter.client import extract_content, parse_json_object
from worker.ai_skills.transcript_interpreter.models import ProcessSummaryInterpretation, WorkflowCapabilityInterpretation
from worker.ai_skills.transcript_interpreter.normalization import (
    calibrate_confidence,
    normalize_confidence,
    normalize_label_list,
    summary_quality_points,
    workflow_evidence_points,
)
from worker.ai_skills.transcript_interpreter.workflow_prompts import PROCESS_SUMMARY_PROMPT, WORKFLOW_CAPABILITY_PROMPT
from worker.ai_skills.transcript_interpreter.workflow_runtime import post_json


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
            {"role": "system", "content": PROCESS_SUMMARY_PROMPT},
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
    parsed = parse_json_object(
        extract_content(post_json(settings=settings, payload=payload, context="process summary generation"))
    )
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
            {"role": "system", "content": WORKFLOW_CAPABILITY_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "document_type": document_type,
                        "process_title": process_title,
                        "workflow_summary": workflow_summary,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
    }
    parsed = parse_json_object(
        extract_content(post_json(settings=settings, payload=payload, context="workflow capability classification"))
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
