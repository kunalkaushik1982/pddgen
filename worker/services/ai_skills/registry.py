from __future__ import annotations

from collections.abc import Callable
import importlib.util
from pathlib import Path
import sys
from typing import Any

from worker.services.ai_skills.base import AISkill


class AISkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, Callable[[], AISkill[Any, Any]]] = {}

    def register(self, key: str, factory: Callable[[], AISkill[Any, Any]]) -> None:
        self._skills[key] = factory

    def create(self, key: str) -> AISkill[Any, Any]:
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
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load AI skill module from {skill_path}.")
        module = importlib.util.module_from_spec(spec)
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


def _load_workflow_title_resolution_skill() -> type[Any]:
    return _load_skill_type(
        "worker.services.ai_skills.workflow_title_resolution.skill",
        local_name="workflow_title_resolution_skill_registry_local",
        relative_path="workflow_title_resolution/skill.py",
        class_name="WorkflowTitleResolutionSkill",
    )


def _load_workflow_group_match_skill() -> type[Any]:
    return _load_skill_type(
        "worker.services.ai_skills.workflow_group_match.skill",
        local_name="workflow_group_match_skill_registry_local",
        relative_path="workflow_group_match/skill.py",
        class_name="WorkflowGroupMatchSkill",
    )


def _load_process_summary_generation_skill() -> type[Any]:
    return _load_skill_type(
        "worker.services.ai_skills.process_summary_generation.skill",
        local_name="process_summary_generation_skill_registry_local",
        relative_path="process_summary_generation/skill.py",
        class_name="ProcessSummaryGenerationSkill",
    )


def _load_diagram_generation_skill() -> type[Any]:
    return _load_skill_type(
        "worker.services.ai_skills.diagram_generation.skill",
        local_name="diagram_generation_skill_registry_local",
        relative_path="diagram_generation/skill.py",
        class_name="DiagramGenerationSkill",
    )


def _load_workflow_capability_tagging_skill() -> type[Any]:
    return _load_skill_type(
        "worker.services.ai_skills.workflow_capability_tagging.skill",
        local_name="workflow_capability_tagging_skill_registry_local",
        relative_path="workflow_capability_tagging/skill.py",
        class_name="WorkflowCapabilityTaggingSkill",
    )


def build_default_ai_skill_registry() -> AISkillRegistry:
    registry = AISkillRegistry()
    registry.register("transcript_to_steps", _load_transcript_to_steps_skill())
    registry.register("semantic_enrichment", _load_semantic_enrichment_skill())
    registry.register("workflow_boundary_detection", _load_workflow_boundary_detection_skill())
    registry.register("workflow_title_resolution", _load_workflow_title_resolution_skill())
    registry.register("workflow_group_match", _load_workflow_group_match_skill())
    registry.register("process_summary_generation", _load_process_summary_generation_skill())
    registry.register("diagram_generation", _load_diagram_generation_skill())
    registry.register("workflow_capability_tagging", _load_workflow_capability_tagging_skill())
    return registry
