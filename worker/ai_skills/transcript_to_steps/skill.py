from __future__ import annotations

import importlib.util
import logging
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from worker.ai_skills.client import OpenAICompatibleSkillClient
    from worker.ai_skills.transcript_to_steps.schemas import (
        TranscriptNote,
        TranscriptStep,
        TranscriptToStepsRequest,
        TranscriptToStepsResponse,
    )

try:
    from worker.ai_skills.client import OpenAICompatibleSkillClient as _OpenAICompatibleSkillClient, extract_message_content
    from worker.ai_skills.runtime import load_markdown_text, parse_json_object
    from worker.ai_skills.transcript_to_steps.schemas import (
        TranscriptNote as _TranscriptNote,
        TranscriptStep as _TranscriptStep,
        TranscriptToStepsRequest as _TranscriptToStepsRequest,
        TranscriptToStepsResponse as _TranscriptToStepsResponse,
    )
except Exception:
    _BASE_DIR = Path(__file__).resolve().parent

    def _load_local_module(name: str, path: Path):
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load module {name!r} from {path}.")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    _client_module = _load_local_module("ai_skill_client_local", _BASE_DIR.parent / "client.py")
    _runtime_module = _load_local_module("ai_skill_runtime_local", _BASE_DIR.parent / "runtime.py")
    _schemas_module = _load_local_module("transcript_to_steps_schemas_local", _BASE_DIR / "schemas.py")

    _OpenAICompatibleSkillClient = _client_module.OpenAICompatibleSkillClient
    extract_message_content = _client_module.extract_message_content
    load_markdown_text = _runtime_module.load_markdown_text
    parse_json_object = _runtime_module.parse_json_object
    _TranscriptNote = _schemas_module.TranscriptNote
    _TranscriptStep = _schemas_module.TranscriptStep
    _TranscriptToStepsRequest = _schemas_module.TranscriptToStepsRequest
    _TranscriptToStepsResponse = _schemas_module.TranscriptToStepsResponse

TIMESTAMP_PATTERN = re.compile(r"\b(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\b")
logger = logging.getLogger(__name__)


def normalize_confidence(value: str) -> str:
    normalized = str(value or "medium").lower()
    return normalized if normalized in {"high", "medium", "low", "unknown"} else "medium"


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


class TranscriptToStepsSkill:
    skill_id = "transcript_to_steps"
    version = "1.0"

    def __init__(self, client: OpenAICompatibleSkillClient | None = None) -> None:
        self.client = client

    def build_messages(self, request: TranscriptToStepsRequest) -> list[dict[str, str]]:
        prompt_path = Path(__file__).with_name("prompt.md")
        prompt_text = load_markdown_text(prompt_path)
        return [
            {"role": "system", "content": prompt_text},
            {
                "role": "user",
                "content": f"Convert this transcript into process steps and business rules.\n\nTranscript:\n{request.transcript_text}",
            },
        ]

    def run(self, input: TranscriptToStepsRequest) -> TranscriptToStepsResponse:
        client = self.client or _OpenAICompatibleSkillClient()
        logger.info(
            "Executing AI skill.",
            extra={
                "skill_id": self.skill_id,
                "skill_version": self.version,
                "transcript_artifact_id": input.transcript_artifact_id,
            },
        )
        response_body = client.post_json(messages=self.build_messages(input), skill_id=self.skill_id)
        content = extract_message_content(response_body)
        parsed = parse_json_object(content)
        steps = [
            _TranscriptStep(
                application_name=str(item.get("application_name", "") or ""),
                action_text=str(item.get("action_text", "") or "").strip(),
                source_data_note=str(item.get("source_data_note", "") or "").strip(),
                start_timestamp=normalize_timestamp(str(item.get("start_timestamp", "") or "")),
                end_timestamp=normalize_timestamp(str(item.get("end_timestamp", "") or "")),
                display_timestamp=normalize_timestamp(str(item.get("display_timestamp", item.get("timestamp", "")) or "")),
                supporting_transcript_text=str(item.get("supporting_transcript_text", "") or "").strip(),
                confidence=normalize_confidence(str(item.get("confidence", "") or "")),
            )
            for item in parsed.get("steps", [])
            if isinstance(item, dict)
        ]
        notes = [
            _TranscriptNote(
                text=str(item.get("text", "") or "").strip(),
                confidence=normalize_confidence(str(item.get("confidence", "") or "")),
                inference_type=str(item.get("inference_type", "inferred") or "inferred"),
            )
            for item in parsed.get("notes", [])
            if isinstance(item, dict)
        ]
        return _TranscriptToStepsResponse(steps=steps, notes=notes)
