r"""
Purpose: Background task for long-running draft generation work.
Full filepath: C:\Users\work\Documents\PddGenerator\worker\tasks\draft_generation.py
"""

from worker.celery_app import celery_app
from app.core.observability import bind_log_context, get_logger
from worker.pipeline.stages.worker import DraftGenerationWorker

logger = get_logger(__name__)


@celery_app.task(name="draft_generation.run", bind=True, autoretry_for=(RuntimeError,), retry_backoff=True, max_retries=3)
def run_draft_generation(self, session_id: str) -> dict[str, int | str]:
    """Run the draft generation pipeline in the background."""
    with bind_log_context(task_id=self.request.id, session_id=session_id):
        logger.info("Draft generation task started", extra={"event": "draft_generation.task_started"})
        worker = DraftGenerationWorker(task_id=self.request.id)
        try:
            result = worker.run(session_id)
            logger.info("Draft generation task completed", extra={"event": "draft_generation.task_completed"})
            return result
        except ValueError as exc:
            logger.exception("Draft generation task failed", extra={"event": "draft_generation.task_failed"})
            raise RuntimeError(str(exc)) from exc
