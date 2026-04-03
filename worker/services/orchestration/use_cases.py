from __future__ import annotations

from collections.abc import Sequence

from worker.services.orchestration.contracts import (
    DraftContextLoader,
    DraftPipelineStage,
    DraftResultPersister,
    DraftSessionRepository,
    FailureRecorder,
    ScreenshotContextBuilder,
    ScreenshotLockManager,
    ScreenshotPipelineStage,
    ScreenshotResultPersister,
    WorkerUnitOfWorkFactory,
)
from worker.services.orchestration.pipeline import OrderedStageRunner


class DraftGenerationUseCase:
    def __init__(
        self,
        *,
        uow_factory: WorkerUnitOfWorkFactory,
        repository: DraftSessionRepository,
        context_loader: DraftContextLoader,
        stages: Sequence[DraftPipelineStage],
        persister: DraftResultPersister,
        failure_recorder: FailureRecorder | None,
    ) -> None:
        self._uow_factory = uow_factory
        self._repository = repository
        self._context_loader = context_loader
        self._stages = OrderedStageRunner(stages)
        self._persister = persister
        self._failure_recorder = failure_recorder

    def run(self, *, session_id: str) -> dict[str, int | str]:
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


class ScreenshotGenerationUseCase:
    def __init__(
        self,
        *,
        uow_factory: WorkerUnitOfWorkFactory,
        repository: DraftSessionRepository,
        context_builder: ScreenshotContextBuilder,
        stages: Sequence[ScreenshotPipelineStage],
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
