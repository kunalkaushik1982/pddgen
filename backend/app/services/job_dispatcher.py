r"""
Purpose: Queue draft-generation and screenshot work onto the background worker.

Depends on `JobEnqueuePort` and `ScreenshotRunGuardPort` only — broker and lock implementations
are injected (see `app.portability.job_messaging`).
"""

from app.core.config import get_settings
from app.core.observability import get_logger
from app.portability.job_messaging import JobEnqueuePort, ScreenshotRunGuardPort


logger = get_logger(__name__)


class JobDispatcherService:
    """Dispatch long-running generation work to the worker queue."""

    def __init__(self, *, enqueue: JobEnqueuePort, screenshot_run_guard: ScreenshotRunGuardPort) -> None:
        self.settings = get_settings()
        self._enqueue = enqueue
        self._screenshot_run_guard = screenshot_run_guard

    def acquire_screenshot_generation_lock(self, session_id: str) -> bool:
        """Acquire a short-lived reservation to prevent duplicate screenshot jobs per session."""
        return self._screenshot_run_guard.try_reserve(session_id)

    def release_screenshot_generation_lock(self, session_id: str) -> None:
        """Release the duplicate-prevention screenshot generation reservation."""
        self._screenshot_run_guard.release(session_id)

    def enqueue_draft_generation(self, session_id: str) -> str:
        """Queue the draft-generation task and return the task id."""
        task = self._enqueue.enqueue("draft_generation.run", [session_id], queue="draft-generation")
        logger.info(
            "Queued draft generation task",
            extra={"event": "draft_generation.queued", "session_id": session_id, "task_id": task.id},
        )
        return task.id

    def enqueue_screenshot_generation(self, session_id: str) -> str:
        """Queue the screenshot-generation task and return the task id."""
        task = self._enqueue.enqueue("screenshot_generation.run", [session_id], queue="draft-generation")
        logger.info(
            "Queued screenshot generation task",
            extra={"event": "screenshot_generation.queued", "session_id": session_id, "task_id": task.id},
        )
        return task.id
