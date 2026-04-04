from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from worker.pipeline.contracts import PipelineStage
from worker.pipeline.stages.stage_context import DraftGenerationContext


class OrderedStageRunner:
    def __init__(self, stages: Sequence[PipelineStage]) -> None:
        self._stages = list(stages)

    def run(self, db: Session, context: DraftGenerationContext) -> None:
        for stage in self._stages:
            stage.run(db, context)
