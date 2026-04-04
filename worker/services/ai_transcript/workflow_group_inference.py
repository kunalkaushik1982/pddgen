from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from worker.services.ai_transcript.client import extract_content, parse_json_object
from worker.services.ai_transcript.models import ProcessGroupInterpretation
from worker.services.ai_transcript.workflow_prompts import PROCESS_GROUP_INFERENCE_PROMPT
from worker.services.ai_transcript.workflow_runtime import post_json


def infer_process_group(
    *,
    settings: Any,
    transcript_name: str,
    steps: Sequence[Mapping[str, Any]],
    notes: Sequence[Mapping[str, Any]],
    existing_titles: list[str],
) -> ProcessGroupInterpretation | None:
    payload = {
        "model": settings.ai_model,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": PROCESS_GROUP_INFERENCE_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "transcript_name": transcript_name,
                        "existing_titles": existing_titles,
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
    parsed = parse_json_object(extract_content(post_json(settings=settings, payload=payload, context="process-group inference")))
    process_title = str(parsed.get("process_title", "") or "").strip()
    canonical_slug = str(parsed.get("canonical_slug", "") or "").strip().lower()
    matched_existing_title = str(parsed.get("matched_existing_title", "") or "").strip() or None
    if not process_title:
        return None
    return ProcessGroupInterpretation(
        process_title=process_title,
        canonical_slug=canonical_slug,
        matched_existing_title=matched_existing_title,
    )
