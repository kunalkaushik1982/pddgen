from __future__ import annotations

import importlib.util
import json
import logging
import re
import sys
from pathlib import Path

try:
    from worker.services.ai_skills.client import OpenAICompatibleSkillClient, extract_message_content
    from worker.services.ai_skills.runtime import load_markdown_text, parse_json_object
    from worker.services.ai_skills.workflow_capability_tagging.schemas import (
        WorkflowCapabilityTaggingRequest,
        WorkflowCapabilityTaggingResponse,
    )
except Exception:
    _BASE_DIR = Path(__file__).resolve().parent

    def _load_local_module(name: str, path: Path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    _client_module = _load_local_module("ai_skill_client_local_capability_tagging", _BASE_DIR.parent / "client.py")
    _runtime_module = _load_local_module("ai_skill_runtime_local_capability_tagging", _BASE_DIR.parent / "runtime.py")
    _schemas_module = _load_local_module("workflow_capability_tagging_schemas_local", _BASE_DIR / "schemas.py")

    OpenAICompatibleSkillClient = _client_module.OpenAICompatibleSkillClient
    extract_message_content = _client_module.extract_message_content
    load_markdown_text = _runtime_module.load_markdown_text
    parse_json_object = _runtime_module.parse_json_object
    WorkflowCapabilityTaggingRequest = _schemas_module.WorkflowCapabilityTaggingRequest
    WorkflowCapabilityTaggingResponse = _schemas_module.WorkflowCapabilityTaggingResponse

logger = logging.getLogger(__name__)


def normalize_confidence(value: str) -> str:
    normalized = str(value or "medium").lower()
    return normalized if normalized in {"high", "medium", "low", "unknown"} else "medium"


def _normalize_textish(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9\s]+", " ", value.lower())
    return re.sub(r"\s+", " ", normalized).strip()


def normalize_capability_tags(values: object, *, process_title: str) -> list[str]:
    if not isinstance(values, list):
        return []
    excluded = _normalize_textish(process_title)
    normalized_items: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = " ".join(str(value or "").split()).strip()
        normalized_key = _normalize_textish(cleaned)
        if not cleaned or not normalized_key or normalized_key == excluded or normalized_key in seen:
            continue
        seen.add(normalized_key)
        normalized_items.append(cleaned)
        if len(normalized_items) >= 3:
            break
    return normalized_items


class WorkflowCapabilityTaggingSkill:
    skill_id = "workflow_capability_tagging"
    version = "1.0"

    def __init__(self, client: OpenAICompatibleSkillClient | None = None) -> None:
        self.client = client

    def build_messages(self, request: WorkflowCapabilityTaggingRequest) -> list[dict[str, str]]:
        prompt_path = Path(__file__).with_name("prompt.md")
        prompt_text = load_markdown_text(prompt_path)
        return [
            {"role": "system", "content": prompt_text},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "document_type": request.document_type,
                        "process_title": request.process_title,
                        "workflow_summary": request.workflow_summary,
                    },
                    ensure_ascii=False,
                ),
            },
        ]

    def run(self, input: WorkflowCapabilityTaggingRequest) -> WorkflowCapabilityTaggingResponse:
        client = self.client or OpenAICompatibleSkillClient()
        logger.info(
            "Executing AI skill.",
            extra={
                "skill_id": self.skill_id,
                "skill_version": self.version,
                "process_title": input.process_title,
            },
        )
        response_body = client.post_json(messages=self.build_messages(input))
        content = extract_message_content(response_body)
        parsed = parse_json_object(content)
        return WorkflowCapabilityTaggingResponse(
            capability_tags=normalize_capability_tags(
                parsed.get("capability_tags", []),
                process_title=input.process_title,
            ),
            confidence=normalize_confidence(str(parsed.get("confidence", "") or "")),
            rationale=str(parsed.get("rationale", "") or "").strip(),
        )
