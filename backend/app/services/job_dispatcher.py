r"""
Purpose: Queue draft-generation work onto the Celery worker.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\job_dispatcher.py
"""

from celery import Celery

from app.core.config import get_settings
from app.core.observability import get_logger


logger = get_logger(__name__)


class JobDispatcherService:
    """Dispatch long-running generation work to the worker queue."""

    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.client = Celery("pdd_generator_backend", broker=settings.redis_url, backend=settings.redis_url)

    @staticmethod
    def _screenshot_lock_key(session_id: str) -> str:
        return f"pdd-generator:screenshot-generation-lock:{session_id}"

    def acquire_screenshot_generation_lock(self, session_id: str) -> bool:
        """Acquire a short-lived lock to prevent duplicate screenshot jobs per session."""
        backend_client = getattr(self.client.backend, "client", None)
        if backend_client is None:
            return True
        lock_key = self._screenshot_lock_key(session_id)
        return bool(
            backend_client.set(
                lock_key,
                "1",
                ex=self.settings.screenshot_generation_lock_seconds,
                nx=True,
            )
        )

    def release_screenshot_generation_lock(self, session_id: str) -> None:
        """Release the duplicate-prevention screenshot generation lock."""
        backend_client = getattr(self.client.backend, "client", None)
        if backend_client is None:
            return
        backend_client.delete(self._screenshot_lock_key(session_id))

    def enqueue_draft_generation(self, session_id: str) -> str:
        """Queue the draft-generation task and return the task id."""
        task = self.client.send_task("draft_generation.run", args=[session_id], queue="draft-generation")
        logger.info(
            "Queued draft generation task",
            extra={"event": "draft_generation.queued", "session_id": session_id, "task_id": task.id},
        )
        return task.id

    def enqueue_screenshot_generation(self, session_id: str) -> str:
        """Queue the screenshot-generation task and return the task id."""
        task = self.client.send_task("screenshot_generation.run", args=[session_id], queue="draft-generation")
        logger.info(
            "Queued screenshot generation task",
            extra={"event": "screenshot_generation.queued", "session_id": session_id, "task_id": task.id},
        )
        return task.id
