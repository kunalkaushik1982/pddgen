from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from app.models.draft_session import DraftSessionModel
from sqlalchemy.orm import Session

from worker.pipeline.stages.stage_context import DraftGenerationContext


class WorkerUnitOfWork(Protocol):
    """Minimal transactional scope for one pipeline run."""

    @property
    def session(self) -> Session: ...

    def __enter__(self) -> WorkerUnitOfWork: ...
    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool | None: ...


WorkerUnitOfWorkFactory = Callable[[], WorkerUnitOfWork]


class DraftSessionRepository(Protocol):
    """Load a draft session from persistent storage."""

    def load_draft_session(self, db: Session, session_id: str) -> DraftSessionModel: ...


class DraftContextLoader(Protocol):
    """Prepare and return the initial pipeline execution context."""

    def __call__(self, db: Session, session: DraftSessionModel) -> DraftGenerationContext: ...


class PipelineStage(Protocol):
    """A single step in an ordered pipeline run (draft and screenshot pipelines share context type)."""

    def run(self, db: Session, context: DraftGenerationContext) -> None: ...


class DraftResultPersister(Protocol):
    """Persist the outputs of a completed draft generation run."""

    def persist(self, db: Session, context: DraftGenerationContext) -> dict[str, int | str]: ...


class FailureRecorder(Protocol):
    """Record a pipeline failure against the session."""

    def record_failure(self, db: Session, session_id: str, detail: str | None = None) -> None: ...


class ScreenshotContextBuilder(Protocol):
    """Build the execution context for a screenshot-only pipeline run."""

    def build(self, db: Session, session: DraftSessionModel) -> DraftGenerationContext: ...


class ScreenshotResultPersister(Protocol):
    """Persist screenshot outputs after a screenshot pipeline run."""

    def persist(self, db: Session, context: DraftGenerationContext) -> dict[str, int | str]: ...


class ScreenshotLockManager(Protocol):
    """Release the per-session screenshot generation lock."""

    def release(self, session_id: str) -> None: ...
