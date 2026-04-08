from __future__ import annotations

from collections.abc import Sequence

from worker.pipeline.contracts import (
    DraftContextLoader,
    DraftLockManager,
    DraftResultPersister,
    DraftSessionRepository,
    FailureRecorder,
    PipelineStage,
    ScreenshotContextBuilder,
    ScreenshotLockManager,
    ScreenshotResultPersister,
    WorkerUnitOfWorkFactory,
)
from worker.pipeline.pipeline import OrderedStageRunner


class DraftGenerationUseCase:
    def __init__(
        self,
        *,
        uow_factory: WorkerUnitOfWorkFactory,
        repository: DraftSessionRepository,
        context_loader: DraftContextLoader,
        stages: Sequence[PipelineStage],
        persister: DraftResultPersister,
        failure_recorder: FailureRecorder | None,
        lock_manager: DraftLockManager | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._repository = repository
        self._context_loader = context_loader
        self._stages = OrderedStageRunner(stages)
        self._persister = persister
        self._failure_recorder = failure_recorder
        self._lock_manager = lock_manager

    def run(self, *, session_id: str) -> dict[str, int | str]:
        try:
            with self._uow_factory() as uow:
                try:
                    session = self._repository.load_draft_session(uow.session, session_id)
                    context = self._context_loader(uow.session, session)
                    self._stages.run(uow.session, context)
                    return self._persister.persist(uow.session, context)
                except Exception as exc:
                    if self._failure_recorder is not None:
                        self._failure_recorder.record_failure(uow.session, session_id, str(exc))
                    raise
        finally:
            if self._lock_manager is not None:
                self._lock_manager.release(session_id)


class ScreenshotGenerationUseCase:
    def __init__(
        self,
        *,
        uow_factory: WorkerUnitOfWorkFactory,
        repository: DraftSessionRepository,
        context_builder: ScreenshotContextBuilder,
        stages: Sequence[PipelineStage],
        persister: ScreenshotResultPersister,
        lock_manager: ScreenshotLockManager,
    ) -> None:
        self._uow_factory = uow_factory
        self._repository = repository
        self._context_builder = context_builder
        self._stages = OrderedStageRunner(stages)
        self._persister = persister
        self._lock_manager = lock_manager

    def run(self, *, session_id: str) -> dict[str, int | str]:
        try:
            with self._uow_factory() as uow:
                session = self._repository.load_draft_session(uow.session, session_id)
                context = self._context_builder.build(uow.session, session)
                self._stages.run(uow.session, context)
                return self._persister.persist(uow.session, context)
        finally:
            self._lock_manager.release(session_id)
