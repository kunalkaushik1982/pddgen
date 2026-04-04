from __future__ import annotations

import importlib.util
import json
import logging
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from worker.ai_skills.client import OpenAICompatibleSkillClient
    from worker.ai_skills.workflow_group_match.schemas import (
        WorkflowGroupMatchRequest,
        WorkflowGroupMatchResponse,
    )

try:
    from worker.ai_skills.client import OpenAICompatibleSkillClient as _OpenAICompatibleSkillClient, extract_message_content
    from worker.ai_skills.runtime import load_markdown_text, parse_json_object
    from worker.ai_skills.workflow_group_match.schemas import (
        WorkflowGroupMatchRequest as _WorkflowGroupMatchRequest,
        WorkflowGroupMatchResponse as _WorkflowGroupMatchResponse,
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

    _client_module = _load_local_module("ai_skill_client_local_group_match", _BASE_DIR.parent / "client.py")
    _runtime_module = _load_local_module("ai_skill_runtime_local_group_match", _BASE_DIR.parent / "runtime.py")
    _schemas_module = _load_local_module("workflow_group_match_schemas_local", _BASE_DIR / "schemas.py")

    _OpenAICompatibleSkillClient = _client_module.OpenAICompatibleSkillClient
    extract_message_content = _client_module.extract_message_content
    load_markdown_text = _runtime_module.load_markdown_text
    parse_json_object = _runtime_module.parse_json_object
    _WorkflowGroupMatchRequest = _schemas_module.WorkflowGroupMatchRequest
    _WorkflowGroupMatchResponse = _schemas_module.WorkflowGroupMatchResponse

logger = logging.getLogger(__name__)
_SLUG_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalize_confidence(value: str) -> str:
    normalized = str(value or "medium").lower()
    return normalized if normalized in {"high", "medium", "low", "unknown"} else "medium"


def normalize_title(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def normalize_slug(value: object, *, fallback: str) -> str:
    candidate = str(value or "").strip().lower() or fallback.strip().lower()
    normalized = _SLUG_NON_ALNUM.sub("-", candidate).strip("-")
    return normalized or "workflow"


class WorkflowGroupMatchSkill:
    skill_id = "workflow_group_match"
    version = "1.0"

    def __init__(self, client: OpenAICompatibleSkillClient | None = None) -> None:
        self.client = client

    def build_messages(self, request: WorkflowGroupMatchRequest) -> list[dict[str, str]]:
        prompt_path = Path(__file__).with_name("prompt.md")
        prompt_text = load_markdown_text(prompt_path)
        return [
            {"role": "system", "content": prompt_text},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "transcript_name": request.transcript_name,
                        "workflow_summary": request.workflow_summary,
                        "existing_group_titles": [str(group.get("title", "") or "") for group in request.existing_groups],
                        "existing_groups": request.existing_groups,
                    },
                    ensure_ascii=False,
                ),
            },
        ]

    def run(self, input: WorkflowGroupMatchRequest) -> WorkflowGroupMatchResponse:
        client = self.client or _OpenAICompatibleSkillClient()
        logger.info(
            "Executing AI skill.",
            extra={
                "skill_id": self.skill_id,
                "skill_version": self.version,
                "transcript_name": input.transcript_name,
            },
        )
        response_body = client.post_json(messages=self.build_messages(input))
        content = extract_message_content(response_body)
        parsed = parse_json_object(content)
        known_titles = {str(group.get("title", "") or "") for group in input.existing_groups if str(group.get("title", "") or "")}
        matched_existing_title = normalize_title(parsed.get("matched_existing_title")) or None
        if matched_existing_title not in known_titles:
            matched_existing_title = None
        recommended_title = normalize_title(parsed.get("recommended_title"))
        fallback_title = matched_existing_title or recommended_title
        return _WorkflowGroupMatchResponse(
            matched_existing_title=matched_existing_title,
            recommended_title=recommended_title,
            recommended_slug=normalize_slug(parsed.get("recommended_slug"), fallback=fallback_title or "workflow"),
            confidence=normalize_confidence(str(parsed.get("confidence", "") or "")),
            rationale=str(parsed.get("rationale", "") or "").strip(),
        )
