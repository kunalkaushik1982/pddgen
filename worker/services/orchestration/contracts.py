from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol


class WorkerUnitOfWork(Protocol):
    session: Any

    def __enter__(self) -> "WorkerUnitOfWork": ...
    def __exit__(self, exc_type, exc, tb) -> bool | None: ...


WorkerUnitOfWorkFactory = Callable[[], WorkerUnitOfWork]


class DraftSessionRepository(Protocol):
    def load_draft_session(self, db: Any, session_id: str) -> Any: ...


class DraftContextLoader(Protocol):
    def __call__(self, db: Any, session: Any) -> Any: ...


class DraftPipelineStage(Protocol):
    def run(self, db: Any, context: Any) -> None: ...


class DraftResultPersister(Protocol):
    def persist(self, db: Any, context: Any) -> dict[str, int | str]: ...


class FailureRecorder(Protocol):
    def record_failure(self, db: Any, session_id: str, detail: str | None = None) -> None: ...


class ScreenshotContextBuilder(Protocol):
    def build(self, db: Any, session: Any) -> Any: ...


class ScreenshotPipelineStage(Protocol):
    def run(self, db: Any, context: Any) -> None: ...


class ScreenshotResultPersister(Protocol):
    def persist(self, db: Any, context: Any) -> dict[str, int | str]: ...


class ScreenshotLockManager(Protocol):
    def release(self, session_id: str) -> None: ...


@dataclass(slots=True)
class DraftPipelineDefinition:
    context_loader: DraftContextLoader
    stages: Sequence[DraftPipelineStage]
    persister: DraftResultPersister
