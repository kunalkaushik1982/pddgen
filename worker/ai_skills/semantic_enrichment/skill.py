from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from worker.ai_skills.client import OpenAICompatibleSkillClient
    from worker.ai_skills.semantic_enrichment.schemas import (
        SemanticEnrichmentRequest,
        SemanticEnrichmentResponse,
    )

try:
    from worker.ai_skills.client import OpenAICompatibleSkillClient as _OpenAICompatibleSkillClient, extract_message_content
    from worker.ai_skills.runtime import load_markdown_text, parse_json_object
    from worker.ai_skills.semantic_enrichment.schemas import (
        SemanticEnrichmentRequest as _SemanticEnrichmentRequest,
        SemanticEnrichmentResponse as _SemanticEnrichmentResponse,
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

    _client_module = _load_local_module("ai_skill_client_local_semantic", _BASE_DIR.parent / "client.py")
    _runtime_module = _load_local_module("ai_skill_runtime_local_semantic", _BASE_DIR.parent / "runtime.py")
    _schemas_module = _load_local_module("semantic_enrichment_schemas_local", _BASE_DIR / "schemas.py")

    _OpenAICompatibleSkillClient = _client_module.OpenAICompatibleSkillClient
    extract_message_content = _client_module.extract_message_content
    load_markdown_text = _runtime_module.load_markdown_text
    parse_json_object = _runtime_module.parse_json_object
    _SemanticEnrichmentRequest = _schemas_module.SemanticEnrichmentRequest
    _SemanticEnrichmentResponse = _schemas_module.SemanticEnrichmentResponse

logger = logging.getLogger(__name__)


def normalize_confidence(value: str) -> str:
    normalized = str(value or "medium").lower()
    return normalized if normalized in {"high", "medium", "low", "unknown"} else "medium"


def normalize_label_list(values: object, *, max_items: int) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized_items: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        cleaned = " ".join(value.split()).strip()
        key = cleaned.lower()
        if not cleaned or key in seen:
            continue
        seen.add(key)
        normalized_items.append(cleaned)
        if len(normalized_items) >= max_items:
            break
    return normalized_items


def normalize_optional_text(value: object) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


class SemanticEnrichmentSkill:
    skill_id = "semantic_enrichment"
    version = "1.0"

    def __init__(self, client: OpenAICompatibleSkillClient | None = None) -> None:
        self.client = client

    def build_messages(self, request: SemanticEnrichmentRequest) -> list[dict[str, str]]:
        prompt_path = Path(__file__).with_name("prompt.md")
        prompt_text = load_markdown_text(prompt_path)
        return [
            {"role": "system", "content": prompt_text},
            {
                "role": "user",
                "content": (
                    "{"
                    f"\"transcript_name\": \"{request.transcript_name}\", "
                    f"\"segment_context\": {request.segment_context}, "
                    f"\"segment_text\": \"{request.segment_text}\""
                    "}"
                ),
            },
        ]

    def run(self, input: SemanticEnrichmentRequest) -> SemanticEnrichmentResponse:
        client = self.client or _OpenAICompatibleSkillClient()
        logger.info(
            "Executing AI skill.",
            extra={
                "skill_id": self.skill_id,
                "skill_version": self.version,
                "transcript_name": input.transcript_name,
            },
        )
        response_body = client.post_json(messages=self.build_messages(input), skill_id=self.skill_id)
        content = extract_message_content(response_body)
        parsed = parse_json_object(content)
        return _SemanticEnrichmentResponse(
            actor=normalize_optional_text(parsed.get("actor")),
            actor_role=normalize_optional_text(parsed.get("actor_role")),
            system_name=normalize_optional_text(parsed.get("system_name")),
            action_verb=normalize_optional_text(parsed.get("action_verb")),
            action_type=normalize_optional_text(parsed.get("action_type")),
            business_object=normalize_optional_text(parsed.get("business_object")),
            workflow_goal=normalize_optional_text(parsed.get("workflow_goal")),
            rule_hints=normalize_label_list(parsed.get("rule_hints", []), max_items=4),
            domain_terms=normalize_label_list(parsed.get("domain_terms", []), max_items=6),
            confidence=normalize_confidence(str(parsed.get("confidence", "") or "")),
            rationale=str(parsed.get("rationale", "") or "").strip(),
        )
