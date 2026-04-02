from __future__ import annotations

import importlib.util
import json
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from worker.services.ai_skills.client import OpenAICompatibleSkillClient
    from worker.services.ai_skills.diagram_generation.schemas import (
        DiagramGenerationRequest,
        DiagramGenerationResponse,
    )

try:
    from worker.services.ai_skills.client import OpenAICompatibleSkillClient as _OpenAICompatibleSkillClient, extract_message_content
    from worker.services.ai_skills.runtime import load_markdown_text, parse_json_object
    from worker.services.ai_skills.diagram_generation.schemas import (
        DiagramGenerationRequest as _DiagramGenerationRequest,
        DiagramGenerationResponse as _DiagramGenerationResponse,
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

    _client_module = _load_local_module("ai_skill_client_local_diagram", _BASE_DIR.parent / "client.py")
    _runtime_module = _load_local_module("ai_skill_runtime_local_diagram", _BASE_DIR.parent / "runtime.py")
    _schemas_module = _load_local_module("diagram_generation_schemas_local", _BASE_DIR / "schemas.py")

    _OpenAICompatibleSkillClient = _client_module.OpenAICompatibleSkillClient
    extract_message_content = _client_module.extract_message_content
    load_markdown_text = _runtime_module.load_markdown_text
    parse_json_object = _runtime_module.parse_json_object
    _DiagramGenerationRequest = _schemas_module.DiagramGenerationRequest
    _DiagramGenerationResponse = _schemas_module.DiagramGenerationResponse

logger = logging.getLogger(__name__)


def normalize_diagram_view(view: dict[str, object], view_type: str, session_title: str) -> dict[str, object]:
    raw_nodes = view.get("nodes", []) if isinstance(view, dict) else []
    raw_edges = view.get("edges", []) if isinstance(view, dict) else []

    nodes: list[dict[str, str]] = []
    node_ids: set[str] = set()
    for index, item in enumerate(raw_nodes if isinstance(raw_nodes, list) else [], start=1):
        if not isinstance(item, dict):
            continue
        node_id = str(item.get("id", "") or f"{view_type}_n{index}").strip()
        if not node_id or node_id in node_ids:
            node_id = f"{view_type}_n{index}"
        node_ids.add(node_id)
        category = str(item.get("category", "process") or "process").strip().lower()
        if category not in {"process", "decision"}:
            category = "process"
        nodes.append(
            {
                "id": node_id,
                "label": str(item.get("label", "") or "").strip() or f"Step {index}",
                "category": category,
                "step_range": str(item.get("step_range", "") or "").strip(),
            }
        )

    edges: list[dict[str, str]] = []
    for index, item in enumerate(raw_edges if isinstance(raw_edges, list) else [], start=1):
        if not isinstance(item, dict):
            continue
        source = str(item.get("source", "") or "").strip()
        target = str(item.get("target", "") or "").strip()
        if source not in node_ids or target not in node_ids:
            continue
        edges.append(
            {
                "id": str(item.get("id", "") or f"{view_type}_e{index}").strip() or f"{view_type}_e{index}",
                "source": source,
                "target": target,
                "label": str(item.get("label", "") or "").strip(),
            }
        )

    if not nodes:
        nodes = [{"id": f"{view_type}_n1", "label": "No process steps available", "category": "process", "step_range": ""}]
        edges = []

    return {
        "diagram_type": "flowchart",
        "view_type": view_type,
        "title": str(view.get("title", "") or session_title).strip() or session_title,
        "nodes": nodes,
        "edges": edges,
    }


class DiagramGenerationSkill:
    skill_id = "diagram_generation"
    version = "1.0"

    def __init__(self, client: OpenAICompatibleSkillClient | None = None) -> None:
        self.client = client

    def build_messages(self, request: DiagramGenerationRequest) -> list[dict[str, str]]:
        prompt_path = Path(__file__).with_name("prompt.md")
        prompt_text = load_markdown_text(prompt_path)
        return [
            {"role": "system", "content": prompt_text},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "session_title": request.session_title,
                        "diagram_type": request.diagram_type,
                        "steps": request.steps,
                        "notes": request.notes,
                    },
                    ensure_ascii=False,
                ),
            },
        ]

    def run(self, input: DiagramGenerationRequest) -> DiagramGenerationResponse | None:
        if input.diagram_type.lower() != "flowchart":
            return None
        client = self.client or _OpenAICompatibleSkillClient()
        logger.info(
            "Executing AI skill.",
            extra={
                "skill_id": self.skill_id,
                "skill_version": self.version,
                "session_title": input.session_title,
            },
        )
        response_body = client.post_json(messages=self.build_messages(input))
        content = extract_message_content(response_body)
        parsed = parse_json_object(content)
        return _DiagramGenerationResponse(
            overview=normalize_diagram_view(parsed.get("overview", {}), "overview", input.session_title),
            detailed=normalize_diagram_view(parsed.get("detailed", {}), "detailed", input.session_title),
        )
