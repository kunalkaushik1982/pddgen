from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from worker.services.ai_transcript.client import extract_content, parse_json_object
from worker.services.ai_transcript.confidence import normalize_confidence
from worker.services.ai_transcript.models import AmbiguousProcessGroupResolution
from worker.services.ai_transcript.workflow_prompts import AMBIGUOUS_PROCESS_GROUP_PROMPT
from worker.services.ai_transcript.workflow_runtime import post_json


def resolve_ambiguous_process_group(
    *,
    settings: Any,
    transcript_name: str,
    inferred_title: str,
    candidate_matches: Sequence[Mapping[str, Any]],
    steps: Sequence[Mapping[str, Any]],
    notes: Sequence[Mapping[str, Any]],
) -> AmbiguousProcessGroupResolution | None:
    payload = {
        "model": settings.ai_model,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": AMBIGUOUS_PROCESS_GROUP_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "transcript_name": transcript_name,
                        "inferred_title": inferred_title,
                        "candidate_titles": [item.get("group_title", "") for item in candidate_matches],
                        "candidate_matches": candidate_matches,
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
        extract_content(post_json(settings=settings, payload=payload, context="ambiguous process-group resolution"))
    )
    recommended_title = str(parsed.get("recommended_title", "") or "").strip() or inferred_title
    recommended_slug = str(parsed.get("recommended_slug", "") or "").strip().lower()
    matched_existing_title = str(parsed.get("matched_existing_title", "") or "").strip() or None
    rationale = str(parsed.get("rationale", "") or "").strip()
    return AmbiguousProcessGroupResolution(
        matched_existing_title=matched_existing_title,
        recommended_title=recommended_title,
        recommended_slug=recommended_slug,
        confidence=normalize_confidence(parsed.get("confidence")),
        rationale=rationale,
    )
