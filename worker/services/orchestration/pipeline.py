from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from worker.services.orchestration.contracts import DraftPipelineStage, ScreenshotPipelineStage


class OrderedStageRunner:
    def __init__(self, stages: Sequence[DraftPipelineStage | ScreenshotPipelineStage]) -> None:
        self._stages = list(stages)

    def run(self, db: Any, context: Any) -> None:
        for stage in self._stages:
            stage.run(db, context)
