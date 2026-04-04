from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol


class WorkerUnitOfWork(Protocol):
    """Minimal transactional scope for one pipeline run."""

    session: Any

    def __enter__(self) -> "WorkerUnitOfWork": ...
    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool | None: ...


WorkerUnitOfWorkFactory = Callable[[], WorkerUnitOfWork]


class DraftSessionRepository(Protocol):
    """Load a draft session from persistent storage."""

    def load_draft_session(self, db: Any, session_id: str) -> Any: ...


class DraftContextLoader(Protocol):
    """Prepare and return the initial pipeline execution context."""

    def __call__(self, db: Any, session: Any) -> Any: ...


# LSP fix: one unified Protocol for all pipeline stages.
# DraftPipelineStage and ScreenshotPipelineStage were identical — merged here.
class PipelineStage(Protocol):
    """A single step in an ordered pipeline run."""

    def run(self, db: Any, context: Any) -> None: ...


# Keep legacy aliases for backward compat — remove in next cleanup pass.
DraftPipelineStage = PipelineStage
ScreenshotPipelineStage = PipelineStage


class DraftResultPersister(Protocol):
    """Persist the outputs of a completed draft generation run."""

    def persist(self, db: Any, context: Any) -> dict[str, int | str]: ...


class FailureRecorder(Protocol):
    """Record a pipeline failure against the session."""

    def record_failure(self, db: Any, session_id: str, detail: str | None = None) -> None: ...


class ScreenshotContextBuilder(Protocol):
    """Build the execution context for a screenshot-only pipeline run."""

    def build(self, db: Any, session: Any) -> Any: ...


class ScreenshotResultPersister(Protocol):
    """Persist screenshot outputs after a screenshot pipeline run."""

    def persist(self, db: Any, context: Any) -> dict[str, int | str]: ...


class ScreenshotLockManager(Protocol):
    """Release the per-session screenshot generation lock."""

    def release(self, session_id: str) -> None: ...


@dataclass(slots=True)
class DraftPipelineDefinition:
    context_loader: DraftContextLoader
    stages: Sequence[PipelineStage]
    persister: DraftResultPersister
