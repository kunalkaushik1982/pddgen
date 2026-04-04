from __future__ import annotations

import importlib.util
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any


class AISkillRegistry:
    """Registry mapping skill keys to skill factories.

    OCP: Open for extension (add rows to _SKILL_REGISTRATIONS),
    closed for modification (no code changes needed to add a skill).
    """

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


# OCP fix: one data-driven table.  Adding a new skill = one new row here.
# Format: (registry_key, import_path_suffix, class_name, relative_file_path)
_SKILL_REGISTRATIONS: list[tuple[str, str, str, str]] = [
    (
        "transcript_to_steps",
        "worker.ai_skills.transcript_to_steps.skill",
        "TranscriptToStepsSkill",
        "transcript_to_steps/skill.py",
    ),
    (
        "semantic_enrichment",
        "worker.ai_skills.semantic_enrichment.skill",
        "SemanticEnrichmentSkill",
        "semantic_enrichment/skill.py",
    ),
    (
        "workflow_boundary_detection",
        "worker.ai_skills.workflow_boundary_detection.skill",
        "WorkflowBoundaryDetectionSkill",
        "workflow_boundary_detection/skill.py",
    ),
    (
        "workflow_title_resolution",
        "worker.ai_skills.workflow_title_resolution.skill",
        "WorkflowTitleResolutionSkill",
        "workflow_title_resolution/skill.py",
    ),
    (
        "workflow_group_match",
        "worker.ai_skills.workflow_group_match.skill",
        "WorkflowGroupMatchSkill",
        "workflow_group_match/skill.py",
    ),
    (
        "process_summary_generation",
        "worker.ai_skills.process_summary_generation.skill",
        "ProcessSummaryGenerationSkill",
        "process_summary_generation/skill.py",
    ),
    (
        "diagram_generation",
        "worker.ai_skills.diagram_generation.skill",
        "DiagramGenerationSkill",
        "diagram_generation/skill.py",
    ),
    (
        "workflow_capability_tagging",
        "worker.ai_skills.workflow_capability_tagging.skill",
        "WorkflowCapabilityTaggingSkill",
        "workflow_capability_tagging/skill.py",
    ),
]


def _load_skill_type(module_import_path: str, *, local_name: str, relative_path: str, class_name: str) -> type[Any]:
    """Load a skill class by import path, falling back to direct file loading."""
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


def build_default_ai_skill_registry() -> AISkillRegistry:
    """Build and return the registry with all standard skills registered."""
    registry = AISkillRegistry()
    for key, import_path, class_name, relative_path in _SKILL_REGISTRATIONS:
        local_name = f"{key}_skill_registry_local"
        registry.register(
            key,
            _load_skill_type(
                import_path,
                local_name=local_name,
                relative_path=relative_path,
                class_name=class_name,
            ),
        )
    return registry
