r"""
Purpose: AI-powered transcript-to-steps interpreter using an OpenAI-compatible API.
Full filepath: C:\Users\work\Documents\PddGenerator\worker\services\ai_transcript_interpreter.py
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import httpx

from worker.bootstrap import get_backend_settings

TIMESTAMP_PATTERN = re.compile(r"\b(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\b")


@dataclass
class TranscriptInterpretation:
    """Structured AI interpretation output."""

    steps: list[dict[str, Any]]
    notes: list[dict[str, Any]]


class AITranscriptInterpreter:
    """Interpret raw transcripts into structured process steps and business rules."""

    def __init__(self) -> None:
        self.settings = get_backend_settings()

    def is_enabled(self) -> bool:
        """Return whether AI interpretation is configured."""
        return bool(self.settings.ai_enabled and self.settings.ai_api_key and self.settings.ai_base_url and self.settings.ai_model)

    def interpret(self, *, transcript_artifact_id: str, transcript_text: str) -> TranscriptInterpretation | None:
        """Call the configured AI provider and return structured transcript output."""
        if not self.is_enabled():
            return None

        payload = {
            "model": self.settings.ai_model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You convert RPA discovery transcripts into structured process steps and business rules. "
                        "Return strict JSON with two keys: steps and notes. "
                        "Each step must include application_name, action_text, source_data_note, "
                        "start_timestamp, end_timestamp, display_timestamp, supporting_transcript_text, confidence. "
                        "Each note must include text, confidence, inference_type. "
                        "Ignore greetings, filler talk, and YouTube-style intros. "
                        "Prefer timestamps from the transcript when present. "
                        "Every returned timestamp must be in HH:MM:SS format. "
                        "If a step has no clear timestamp, return an empty string for that field. "
                        "supporting_transcript_text must contain the exact transcript snippet that supports the step. "
                        "display_timestamp should be the best single timestamp to show in UI and export. "
                        "Confidence must be one of high, medium, low, unknown."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Convert this transcript into process steps and business rules.\n\n"
                        f"Transcript:\n{transcript_text}"
                    ),
                },
            ],
        }

        headers = {
            "Authorization": f"Bearer {self.settings.ai_api_key}",
            "Content-Type": "application/json",
        }
        endpoint = f"{self.settings.ai_base_url.rstrip('/')}/chat/completions"

        with httpx.Client(timeout=60.0) as client:
            response = client.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
            body = response.json()

        content = self._extract_content(body)
        parsed = self._parse_json_object(content)
        steps = [self._normalize_step(item, transcript_artifact_id) for item in parsed.get("steps", [])]
        notes = [self._normalize_note(item) for item in parsed.get("notes", [])]
        return TranscriptInterpretation(steps=steps, notes=notes)

    @staticmethod
    def _extract_content(response_body: dict[str, Any]) -> str:
        """Extract message text from a chat completions response."""
        choices = response_body.get("choices", [])
        if not choices:
            raise ValueError("AI response did not contain any choices.")

        message = choices[0].get("message", {})
        content = message.get("content", "")
        if isinstance(content, list):
            return "".join(item.get("text", "") for item in content if isinstance(item, dict))
        if isinstance(content, str):
            return content
        raise ValueError("AI response content was not in a supported format.")

    @staticmethod
    def _parse_json_object(text: str) -> dict[str, Any]:
        """Parse JSON from the model response, even if wrapped in markdown fences."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
        return json.loads(cleaned)

    @staticmethod
    def _normalize_step(item: dict[str, Any], transcript_artifact_id: str) -> dict[str, Any]:
        """Normalize one AI-produced step into the worker's step shape."""
        start_timestamp = AITranscriptInterpreter._normalize_timestamp(str(item.get("start_timestamp", "") or ""))
        end_timestamp = AITranscriptInterpreter._normalize_timestamp(str(item.get("end_timestamp", "") or ""))
        display_timestamp = AITranscriptInterpreter._normalize_timestamp(
            str(item.get("display_timestamp", item.get("timestamp", "")) or "")
        )
        supporting_transcript_text = str(item.get("supporting_transcript_text", "") or "").strip()
        locator = display_timestamp or start_timestamp or "ai:transcript"
        return {
            "step_number": 0,
            "application_name": str(item.get("application_name", "") or ""),
            "action_text": str(item.get("action_text", "") or "").strip(),
            "source_data_note": str(item.get("source_data_note", "") or "").strip(),
            "timestamp": display_timestamp,
            "start_timestamp": start_timestamp,
            "end_timestamp": end_timestamp,
            "supporting_transcript_text": supporting_transcript_text,
            "screenshot_id": "",
            "confidence": AITranscriptInterpreter._normalize_confidence(item.get("confidence")),
            "evidence_references": json.dumps(
                [
                    {
                        "id": str(uuid4()),
                        "artifact_id": transcript_artifact_id,
                        "kind": "transcript",
                        "locator": locator,
                    }
                ]
            ),
            "edited_by_ba": False,
        }

    @staticmethod
    def _normalize_note(item: dict[str, Any]) -> dict[str, Any]:
        """Normalize one AI-produced note into the worker's note shape."""
        return {
            "text": str(item.get("text", "") or "").strip(),
            "related_step_ids": json.dumps([]),
            "evidence_reference_ids": json.dumps([]),
            "confidence": AITranscriptInterpreter._normalize_confidence(item.get("confidence")),
            "inference_type": str(item.get("inference_type", "inferred") or "inferred"),
        }

    @staticmethod
    def _normalize_confidence(value: Any) -> str:
        """Constrain confidence values to the supported enum."""
        normalized = str(value or "medium").lower()
        return normalized if normalized in {"high", "medium", "low", "unknown"} else "medium"

    @staticmethod
    def _normalize_timestamp(value: str) -> str:
        """Normalize flexible transcript timestamps into HH:MM:SS."""
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
