from __future__ import annotations

import importlib.util
import json
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from worker.ai_skills.client import OpenAICompatibleSkillClient
    from worker.ai_skills.workflow_boundary_detection.schemas import (
        WorkflowBoundaryDetectionRequest,
        WorkflowBoundaryDetectionResponse,
    )

try:
    from worker.ai_skills.client import OpenAICompatibleSkillClient as _OpenAICompatibleSkillClient, extract_message_content
    from worker.ai_skills.runtime import load_markdown_text, parse_json_object
    from worker.ai_skills.workflow_boundary_detection.schemas import (
        WorkflowBoundaryDetectionRequest as _WorkflowBoundaryDetectionRequest,
        WorkflowBoundaryDetectionResponse as _WorkflowBoundaryDetectionResponse,
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

    _client_module = _load_local_module("ai_skill_client_local_boundary", _BASE_DIR.parent / "client.py")
    _runtime_module = _load_local_module("ai_skill_runtime_local_boundary", _BASE_DIR.parent / "runtime.py")
    _schemas_module = _load_local_module("workflow_boundary_detection_schemas_local", _BASE_DIR / "schemas.py")

    _OpenAICompatibleSkillClient = _client_module.OpenAICompatibleSkillClient
    extract_message_content = _client_module.extract_message_content
    load_markdown_text = _runtime_module.load_markdown_text
    parse_json_object = _runtime_module.parse_json_object
    _WorkflowBoundaryDetectionRequest = _schemas_module.WorkflowBoundaryDetectionRequest
    _WorkflowBoundaryDetectionResponse = _schemas_module.WorkflowBoundaryDetectionResponse

logger = logging.getLogger(__name__)


def normalize_decision(value: str) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in {"same_workflow", "new_workflow", "uncertain"} else "uncertain"


def normalize_confidence(value: str) -> str:
    normalized = str(value or "medium").lower()
    return normalized if normalized in {"high", "medium", "low", "unknown"} else "medium"


class WorkflowBoundaryDetectionSkill:
    skill_id = "workflow_boundary_detection"
    version = "1.0"

    def __init__(self, client: OpenAICompatibleSkillClient | None = None) -> None:
        self.client = client

    def build_messages(self, request: WorkflowBoundaryDetectionRequest) -> list[dict[str, str]]:
        prompt_path = Path(__file__).with_name("prompt.md")
        prompt_text = load_markdown_text(prompt_path)
        return [
            {"role": "system", "content": prompt_text},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "left_segment": request.left_segment,
                        "right_segment": request.right_segment,
                    },
                    ensure_ascii=False,
                ),
            },
        ]

    def run(self, input: WorkflowBoundaryDetectionRequest) -> WorkflowBoundaryDetectionResponse:
        client = self.client or _OpenAICompatibleSkillClient()
        logger.info(
            "Executing AI skill.",
            extra={
                "skill_id": self.skill_id,
                "skill_version": self.version,
                "left_segment_id": input.left_segment.get("id", ""),
                "right_segment_id": input.right_segment.get("id", ""),
            },
        )
        response_body = client.post_json(messages=self.build_messages(input))
        content = extract_message_content(response_body)
        parsed = parse_json_object(content)
        return _WorkflowBoundaryDetectionResponse(
            decision=normalize_decision(str(parsed.get("decision", "") or "")),
            confidence=normalize_confidence(str(parsed.get("confidence", "") or "")),
            rationale=str(parsed.get("rationale", "") or "").strip(),
        )
