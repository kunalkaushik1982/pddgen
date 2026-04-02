from __future__ import annotations

from collections.abc import Callable
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
