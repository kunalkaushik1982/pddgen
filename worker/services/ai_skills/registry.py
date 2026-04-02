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


def _load_transcript_to_steps_skill() -> type[Any]:
    try:
        from worker.services.ai_skills.transcript_to_steps.skill import TranscriptToStepsSkill

        return TranscriptToStepsSkill
    except Exception:
        skill_path = Path(__file__).resolve().parent / "transcript_to_steps" / "skill.py"
        spec = importlib.util.spec_from_file_location("transcript_to_steps_skill_registry_local", skill_path)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module.TranscriptToStepsSkill


def build_default_ai_skill_registry() -> AISkillRegistry:
    registry = AISkillRegistry()
    registry.register("transcript_to_steps", _load_transcript_to_steps_skill())
    return registry
