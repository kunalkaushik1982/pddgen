from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from worker.services.orchestration.contracts import DraftPipelineStage, ScreenshotPipelineStage

if TYPE_CHECKING:
    from worker.services.draft_generation.stage_context import DraftGenerationContext


class OrderedStageRunner:
    def __init__(self, stages: Sequence[DraftPipelineStage | ScreenshotPipelineStage]) -> None:
        self._stages = list(stages)

    def run(self, db: Any, context: DraftGenerationContext) -> None:
        for stage in self._stages:
            stage.run(db, context)
