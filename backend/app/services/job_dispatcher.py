r"""
Purpose: Queue draft-generation work onto the Celery worker.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\job_dispatcher.py
"""

from app.core.config import get_settings
from app.core.observability import get_logger
from app.portability.celery_job_queue import build_default_job_queue
from app.portability.contracts import JobQueuePort


logger = get_logger(__name__)


class JobDispatcherService:
    """Dispatch long-running generation work to the worker queue."""

    def __init__(self, queue: JobQueuePort | None = None) -> None:
        settings = get_settings()
        self.settings = settings
        self._queue = queue or build_default_job_queue(settings)

    @staticmethod
    def _screenshot_lock_key(session_id: str) -> str:
        return f"pdd-generator:screenshot-generation-lock:{session_id}"

    def acquire_screenshot_generation_lock(self, session_id: str) -> bool:
        """Acquire a short-lived lock to prevent duplicate screenshot jobs per session."""
        lock_key = self._screenshot_lock_key(session_id)
        return self._queue.try_acquire_lock(
            lock_key,
            ttl_seconds=self.settings.screenshot_generation_lock_seconds,
        )

    def release_screenshot_generation_lock(self, session_id: str) -> None:
        """Release the duplicate-prevention screenshot generation lock."""
        self._queue.release_lock(self._screenshot_lock_key(session_id))

    def enqueue_draft_generation(self, session_id: str) -> str:
        """Queue the draft-generation task and return the task id."""
        task = self._queue.send_named_task("draft_generation.run", [session_id], queue="draft-generation")
        logger.info(
            "Queued draft generation task",
            extra={"event": "draft_generation.queued", "session_id": session_id, "task_id": task.id},
        )
        return task.id

    def enqueue_screenshot_generation(self, session_id: str) -> str:
        """Queue the screenshot-generation task and return the task id."""
        task = self._queue.send_named_task("screenshot_generation.run", [session_id], queue="draft-generation")
        logger.info(
            "Queued screenshot generation task",
            extra={"event": "screenshot_generation.queued", "session_id": session_id, "task_id": task.id},
        )
        return task.id
