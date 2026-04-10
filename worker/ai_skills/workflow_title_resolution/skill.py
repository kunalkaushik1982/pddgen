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
    from worker.ai_skills.workflow_title_resolution.schemas import (
        WorkflowTitleResolutionRequest,
        WorkflowTitleResolutionResponse,
    )

try:
    from worker.ai_skills.client import OpenAICompatibleSkillClient as _OpenAICompatibleSkillClient, extract_message_content
    from worker.ai_skills.runtime import load_markdown_text, parse_json_object
    from worker.ai_skills.workflow_title_resolution.schemas import (
        WorkflowTitleResolutionRequest as _WorkflowTitleResolutionRequest,
        WorkflowTitleResolutionResponse as _WorkflowTitleResolutionResponse,
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

    _client_module = _load_local_module("ai_skill_client_local_title", _BASE_DIR.parent / "client.py")
    _runtime_module = _load_local_module("ai_skill_runtime_local_title", _BASE_DIR.parent / "runtime.py")
    _schemas_module = _load_local_module("workflow_title_resolution_schemas_local", _BASE_DIR / "schemas.py")

    _OpenAICompatibleSkillClient = _client_module.OpenAICompatibleSkillClient
    extract_message_content = _client_module.extract_message_content
    load_markdown_text = _runtime_module.load_markdown_text
    parse_json_object = _runtime_module.parse_json_object
    _WorkflowTitleResolutionRequest = _schemas_module.WorkflowTitleResolutionRequest
    _WorkflowTitleResolutionResponse = _schemas_module.WorkflowTitleResolutionResponse

logger = logging.getLogger(__name__)
_SLUG_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalize_confidence(value: str) -> str:
    normalized = str(value or "medium").lower()
    return normalized if normalized in {"high", "medium", "low", "unknown"} else "medium"


def normalize_title(value: object) -> str | None:
    cleaned = " ".join(str(value or "").split()).strip()
    return cleaned or None


def normalize_slug(value: object, *, fallback: str) -> str:
    candidate = str(value or "").strip().lower() or fallback.strip().lower()
    normalized = _SLUG_NON_ALNUM.sub("-", candidate).strip("-")
    return normalized or "workflow"


class WorkflowTitleResolutionSkill:
    skill_id = "workflow_title_resolution"
    version = "1.0"

    def __init__(self, client: OpenAICompatibleSkillClient | None = None) -> None:
        self.client = client

    def build_messages(self, request: WorkflowTitleResolutionRequest) -> list[dict[str, str]]:
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
                    },
                    ensure_ascii=False,
                ),
            },
        ]

    def run(self, input: WorkflowTitleResolutionRequest) -> WorkflowTitleResolutionResponse | None:
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
        workflow_title = normalize_title(parsed.get("workflow_title"))
        if workflow_title is None:
            return None
        return _WorkflowTitleResolutionResponse(
            workflow_title=workflow_title,
            canonical_slug=normalize_slug(parsed.get("canonical_slug"), fallback=workflow_title),
            confidence=normalize_confidence(str(parsed.get("confidence", "") or "")),
            rationale=str(parsed.get("rationale", "") or "").strip(),
        )
