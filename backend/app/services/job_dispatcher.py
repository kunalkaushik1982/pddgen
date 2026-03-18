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
        self.client = Celery("pdd_generator_backend", broker=settings.redis_url, backend=settings.redis_url)

    def enqueue_draft_generation(self, session_id: str) -> str:
        """Queue the draft-generation task and return the task id."""
        task = self.client.send_task("draft_generation.run", args=[session_id], queue="draft-generation")
        logger.info(
            "Queued draft generation task",
            extra={"event": "draft_generation.queued", "session_id": session_id, "task_id": task.id},
        )
        return task.id
