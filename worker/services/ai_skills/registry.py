from __future__ import annotations

from collections.abc import Callable
import importlib.util
from pathlib import Path
import sys
from typing import Any


class AISkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, Callable[[], Any]] = {}

    def register(self, key: str, factory: Callable[[], Any]) -> None:
        self._skills[key] = factory

    def create(self, key: str) -> Any:
        try:
            return self._skills[key]()
        except KeyError as exc:
            available = ", ".join(sorted(self._skills)) or "none"
            raise ValueError(f"Unknown AI skill '{key}'. Available: {available}.") from exc


def _load_skill_type(module_import_path: str, *, local_name: str, relative_path: str, class_name: str) -> type[Any]:
    try:
        module = __import__(module_import_path, fromlist=[class_name])
        return getattr(module, class_name)
    except Exception:
        skill_path = Path(__file__).resolve().parent / relative_path
        spec = importlib.util.spec_from_file_location(local_name, skill_path)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return getattr(module, class_name)


def _load_transcript_to_steps_skill() -> type[Any]:
    return _load_skill_type(
        "worker.services.ai_skills.transcript_to_steps.skill",
        local_name="transcript_to_steps_skill_registry_local",
        relative_path="transcript_to_steps/skill.py",
        class_name="TranscriptToStepsSkill",
    )


def _load_semantic_enrichment_skill() -> type[Any]:
    return _load_skill_type(
        "worker.services.ai_skills.semantic_enrichment.skill",
        local_name="semantic_enrichment_skill_registry_local",
        relative_path="semantic_enrichment/skill.py",
        class_name="SemanticEnrichmentSkill",
    )


def _load_workflow_boundary_detection_skill() -> type[Any]:
    return _load_skill_type(
        "worker.services.ai_skills.workflow_boundary_detection.skill",
        local_name="workflow_boundary_detection_skill_registry_local",
        relative_path="workflow_boundary_detection/skill.py",
        class_name="WorkflowBoundaryDetectionSkill",
    )


def build_default_ai_skill_registry() -> AISkillRegistry:
    registry = AISkillRegistry()
    registry.register("transcript_to_steps", _load_transcript_to_steps_skill())
    registry.register("semantic_enrichment", _load_semantic_enrichment_skill())
    registry.register("workflow_boundary_detection", _load_workflow_boundary_detection_skill())
    return registry
