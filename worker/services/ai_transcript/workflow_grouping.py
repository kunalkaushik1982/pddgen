from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from worker.services.ai_transcript.client import extract_content, parse_json_object, post_chat_completion
from worker.services.ai_transcript.models import AmbiguousProcessGroupResolution, ProcessGroupInterpretation
from worker.services.ai_transcript.normalization import normalize_confidence


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
            {
                "role": "system",
                "content": (
                    "You classify transcript-derived steps into business process groups. "
                    "Return strict JSON with keys: process_title, canonical_slug, matched_existing_title. "
                    "process_title must be a concise business workflow title such as Sales Order Creation. "
                    "canonical_slug must be lowercase kebab-case and stable. "
                    "matched_existing_title must be either one exact title from existing_titles or an empty string. "
                    "Only match an existing title when the process is genuinely the same workflow. "
                    "If the process is different, return an empty matched_existing_title."
                ),
            },
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
    parsed = parse_json_object(extract_content(_post_json(settings=settings, payload=payload, context="process-group inference")))
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
            {
                "role": "system",
                "content": (
                    "You resolve ambiguous workflow-group assignments for transcript-derived evidence. "
                    "Return strict JSON with keys: matched_existing_title, recommended_title, recommended_slug, confidence, rationale. "
                    "matched_existing_title must be either one exact title from candidate_titles or an empty string if a new workflow should be created. "
                    "recommended_title must be the workflow title that should be used. "
                    "recommended_slug must be lowercase kebab-case. "
                    "confidence must be one of high, medium, low, unknown. "
                    "Prefer matching an existing workflow only if the evidence clearly supports the same business workflow. "
                    "If the evidence is materially different, return an empty matched_existing_title and recommend a new workflow title."
                ),
            },
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
        extract_content(_post_json(settings=settings, payload=payload, context="ambiguous process-group resolution"))
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
