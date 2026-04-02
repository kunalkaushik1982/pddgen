from __future__ import annotations

from typing import Any, Protocol


class AISkill(Protocol):
    skill_id: str
    version: str

    def run(self, input: Any) -> Any:
        ...
