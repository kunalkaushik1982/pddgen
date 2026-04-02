from __future__ import annotations

from collections.abc import Sequence
from typing import Any


class OrderedStageRunner:
    def __init__(self, stages: Sequence[object]) -> None:
        self._stages = list(stages)

    def run(self, db: Any, context: Any) -> None:
        for stage in self._stages:
            stage.run(db, context)
