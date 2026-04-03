from __future__ import annotations

import json
import re
from typing import Any, Mapping
from uuid import uuid4

from worker.services.generation_types import NoteRecord, StepRecord

TIMESTAMP_PATTERN = re.compile(r"\b(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\b")


def normalize_confidence(value: Any) -> str:
    normalized = str(value or "medium").lower()
    return normalized if normalized in {"high", "medium", "low", "unknown"} else "medium"


def confidence_rank(confidence: str) -> int:
    return {"unknown": 0, "low": 1, "medium": 2, "high": 3}.get(confidence, 1)


def confidence_from_rank(rank: int) -> str:
    return {0: "unknown", 1: "low", 2: "medium", 3: "high"}.get(max(0, min(rank, 3)), "low")


def calibrate_confidence(confidence: str, *, evidence_points: int, quality_points: int, lower_when: int = 2) -> str:
    rank = confidence_rank(confidence)
    if evidence_points <= lower_when:
        rank = min(rank, 1)
    elif evidence_points <= lower_when + 1 and rank > 1:
        rank -= 1
    if quality_points <= 0:
        rank = min(rank, 1)
    elif quality_points == 1 and rank > 1:
        rank -= 1
    return confidence_from_rank(rank)


def workflow_evidence_points(workflow_summary: dict[str, Any]) -> int:
    score = 0
    for key in ("top_actors", "top_objects", "top_systems", "top_actions", "top_goals", "top_rules", "top_domain_terms"):
        values = workflow_summary.get(key, [])
        if isinstance(values, list) and any(str(value).strip() for value in values):
            score += 1
    for key in ("step_samples", "note_samples"):
        values = workflow_summary.get(key, [])
        if isinstance(values, list) and any(values):
            score += 1
    return score


def title_quality_points(workflow_title: str) -> int:
    token_count = len([token for token in re.split(r"\s+", workflow_title.strip()) if token])
    if token_count < 2:
        return 0
    if token_count <= 6:
        return 2
    return 1


def summary_quality_points(summary_text: str) -> int:
    sentence_count = len([part for part in re.split(r"[.!?]+", summary_text) if part.strip()])
    if sentence_count < 2:
        return 0
    if sentence_count <= 4:
        return 2
    return 1


def normalize_slug(value: str, *, fallback: str) -> str:
    normalized_source = value.strip() or fallback
    normalized = re.sub(r"[^a-z0-9\s-]+", " ", normalized_source.lower())
    collapsed = re.sub(r"\s+", "-", normalized.strip())
    return re.sub(r"-{2,}", "-", collapsed).strip("-") or "process"


def normalize_existing_title(value: str, *, existing_titles: list[str]) -> str | None:
    candidate = value.strip()
    if not candidate:
        return None
    return candidate if candidate in existing_titles else None


def normalize_label(value: str) -> str:
    normalized = re.sub(r"\s+", " ", value.strip())
    return normalized[:120].strip()


def normalize_textish(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9\s]+", " ", value.lower())
    return re.sub(r"\s+", " ", normalized).strip()


def normalize_label_list(values: Any, *, max_items: int, exclude: set[str] | None = None) -> list[str]:
    if not isinstance(values, list):
        return []
    excluded = {normalize_textish(item) for item in (exclude or set()) if normalize_textish(item)}
    normalized_items: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        cleaned = normalize_label(value)
        if not cleaned:
            continue
        normalized_key = normalize_textish(cleaned)
        if not normalized_key or normalized_key in seen or normalized_key in excluded:
            continue
        seen.add(normalized_key)
        normalized_items.append(cleaned)
        if len(normalized_items) >= max_items:
            break
    return normalized_items


def normalize_timestamp(value: str) -> str:
    if not value:
        return ""
    match = TIMESTAMP_PATTERN.search(value.strip())
    if not match:
        return ""
    hours_group, minutes_group, seconds_group = match.groups()
    hours = int(hours_group or 0)
    minutes = int(minutes_group)
    seconds = int(seconds_group)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def normalize_optional_text(value: Any) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def normalize_step(item: Mapping[str, Any], transcript_artifact_id: str) -> StepRecord:
    start_timestamp = normalize_timestamp(str(item.get("start_timestamp", "") or ""))
    end_timestamp = normalize_timestamp(str(item.get("end_timestamp", "") or ""))
    display_timestamp = normalize_timestamp(str(item.get("display_timestamp", item.get("timestamp", "")) or ""))
    supporting_transcript_text = str(item.get("supporting_transcript_text", "") or "").strip()
    locator = display_timestamp or start_timestamp or "ai:transcript"
    return {
        "id": str(uuid4()),
        "process_group_id": None,
        "meeting_id": None,
        "step_number": 0,
        "application_name": str(item.get("application_name", "") or ""),
        "action_text": str(item.get("action_text", "") or "").strip(),
        "source_data_note": str(item.get("source_data_note", "") or "").strip(),
        "timestamp": display_timestamp,
        "start_timestamp": start_timestamp,
        "end_timestamp": end_timestamp,
        "supporting_transcript_text": supporting_transcript_text,
        "screenshot_id": "",
        "confidence": normalize_confidence(item.get("confidence")),
        "evidence_references": json.dumps(
            [{"id": str(uuid4()), "artifact_id": transcript_artifact_id, "kind": "transcript", "locator": locator}]
        ),
        "edited_by_ba": False,
    }


def normalize_note(item: Mapping[str, Any]) -> NoteRecord:
    return {
        "text": str(item.get("text", "") or "").strip(),
        "related_step_ids": json.dumps([]),
        "evidence_reference_ids": json.dumps([]),
        "confidence": normalize_confidence(item.get("confidence")),
        "inference_type": str(item.get("inference_type", "inferred") or "inferred"),
    }
