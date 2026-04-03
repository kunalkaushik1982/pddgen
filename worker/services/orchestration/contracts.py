from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from app.models.draft_session import DraftSessionModel
    from worker.services.draft_generation.stage_context import DraftGenerationContext


class WorkerDbSession(Protocol):
    def add(self, instance: Any) -> None: ...
    def add_all(self, instances: list[Any] | tuple[Any, ...]) -> None: ...
    def commit(self) -> None: ...
    def execute(self, statement: Any) -> Any: ...
    def flush(self) -> None: ...
    def get(self, entity: Any, ident: Any) -> Any: ...
    def close(self) -> None: ...


class WorkerUnitOfWork(Protocol):
    session: WorkerDbSession

    def __enter__(self) -> "WorkerUnitOfWork": ...
    def __exit__(self, exc_type, exc, tb) -> bool | None: ...


WorkerUnitOfWorkFactory = Callable[[], WorkerUnitOfWork]


class DraftSessionRepository(Protocol):
    def load_draft_session(self, db: WorkerDbSession, session_id: str) -> DraftSessionModel: ...


class DraftContextLoader(Protocol):
    def __call__(self, db: WorkerDbSession, session: DraftSessionModel) -> DraftGenerationContext: ...


class DraftPipelineStage(Protocol):
    def run(self, db: WorkerDbSession, context: DraftGenerationContext) -> None: ...


class DraftResultPersister(Protocol):
    def persist(self, db: WorkerDbSession, context: DraftGenerationContext) -> dict[str, int | str]: ...


class FailureRecorder(Protocol):
    def record_failure(self, db: WorkerDbSession, session_id: str, detail: str | None = None) -> None: ...


class ScreenshotContextBuilder(Protocol):
    def build(self, db: WorkerDbSession, session: DraftSessionModel) -> DraftGenerationContext: ...


class ScreenshotPipelineStage(Protocol):
    def run(self, db: WorkerDbSession, context: DraftGenerationContext) -> None: ...


class ScreenshotResultPersister(Protocol):
    def persist(self, db: WorkerDbSession, context: DraftGenerationContext) -> dict[str, int | str]: ...


class ScreenshotLockManager(Protocol):
    def release(self, session_id: str) -> None: ...


@dataclass(slots=True)
class DraftPipelineDefinition:
    context_loader: DraftContextLoader
    stages: Sequence[DraftPipelineStage]
    persister: DraftResultPersister
