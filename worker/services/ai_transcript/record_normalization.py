from __future__ import annotations

import json
import re
from typing import Any, Mapping
from uuid import uuid4

from worker.services.ai_transcript.confidence import normalize_confidence
from worker.services.generation_types import NoteRecord, StepRecord

TIMESTAMP_PATTERN = re.compile(r"\b(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\b")


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
