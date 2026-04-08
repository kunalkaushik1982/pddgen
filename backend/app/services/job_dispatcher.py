r"""
Purpose: Queue draft-generation and screenshot work onto the background worker.

Depends on `JobEnqueuePort`, `DraftRunGuardPort`, and `ScreenshotRunGuardPort` — broker and lock
implementations are injected (see `app.portability.job_messaging`).
"""

from app.core.config import get_settings
from app.core.observability import get_logger
from app.portability.job_messaging import DraftRunGuardPort, JobEnqueuePort, ScreenshotRunGuardPort
from app.portability.job_messaging.envelope import JobEnvelope, JobType


logger = get_logger(__name__)


class JobDispatcherService:
    """Dispatch long-running generation work to the worker queue."""

    def __init__(
        self,
        *,
        enqueue: JobEnqueuePort,
        draft_run_guard: DraftRunGuardPort,
        screenshot_run_guard: ScreenshotRunGuardPort,
    ) -> None:
        self.settings = get_settings()
        self._enqueue = enqueue
        self._draft_run_guard = draft_run_guard
        self._screenshot_run_guard = screenshot_run_guard

    def acquire_draft_generation_lock(self, session_id: str) -> bool:
        """Acquire a short-lived reservation to prevent duplicate draft jobs per session."""
        return self._draft_run_guard.try_reserve(session_id)

    def release_draft_generation_lock(self, session_id: str) -> None:
        """Release the duplicate-prevention draft generation reservation."""
        self._draft_run_guard.release(session_id)

    def acquire_screenshot_generation_lock(self, session_id: str) -> bool:
        """Acquire a short-lived reservation to prevent duplicate screenshot jobs per session."""
        return self._screenshot_run_guard.try_reserve(session_id)

    def release_screenshot_generation_lock(self, session_id: str) -> None:
        """Release the duplicate-prevention screenshot generation reservation."""
        self._screenshot_run_guard.release(session_id)

    def enqueue_draft_generation(self, session_id: str) -> str:
        """Queue the draft-generation task and return the task id (or SQS message id)."""
        job = JobEnvelope(job_type=JobType.DRAFT_GENERATION, session_id=session_id)
        task = self._enqueue.enqueue(job, queue="draft-generation")
        logger.info(
            "Queued draft generation task",
            extra={"event": "draft_generation.queued", "session_id": session_id, "task_id": task.id},
        )
        return task.id

    def enqueue_screenshot_generation(self, session_id: str) -> str:
        """Queue the screenshot-generation task and return the task id (or SQS message id)."""
        job = JobEnvelope(job_type=JobType.SCREENSHOT_GENERATION, session_id=session_id)
        task = self._enqueue.enqueue(job, queue="draft-generation")
        logger.info(
            "Queued screenshot generation task",
            extra={"event": "screenshot_generation.queued", "session_id": session_id, "task_id": task.id},
        )
        return task.id
