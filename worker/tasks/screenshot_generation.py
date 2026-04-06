r"""
Purpose: Background task for screenshot-only generation work.
Full filepath: C:\Users\work\Documents\PddGenerator\worker\tasks\screenshot_generation.py
"""

from celery.exceptions import SoftTimeLimitExceeded

from worker import bootstrap as _bootstrap  # noqa: F401
from app.core.observability import bind_log_context, get_logger
from app.db.session import SessionLocal
from worker.bootstrap import get_backend_settings
from worker.celery_app import celery_app
from worker.pipeline.stages.failure import FailureStage
from worker.screenshot.worker import ScreenshotGenerationWorker

logger = get_logger(__name__)

_limits = get_backend_settings()


@celery_app.task(
    name="screenshot_generation.run",
    bind=True,
    autoretry_for=(RuntimeError,),
    retry_backoff=True,
    max_retries=3,
    soft_time_limit=_limits.screenshot_celery_soft_time_limit_seconds,
    time_limit=_limits.screenshot_celery_time_limit_seconds,
)
def run_screenshot_generation(self, session_id: str) -> dict[str, int | str]:
    """Run screenshot generation for one existing draft session."""
    with bind_log_context(task_id=self.request.id, session_id=session_id):
        logger.info("Screenshot generation task started", extra={"event": "screenshot_generation.task_started"})
        worker = ScreenshotGenerationWorker(task_id=self.request.id)
        try:
            result = worker.run(session_id)
            logger.info("Screenshot generation task completed", extra={"event": "screenshot_generation.task_completed"})
            return result
        except ValueError as exc:
            logger.exception("Screenshot generation task failed", extra={"event": "screenshot_generation.task_failed"})
            raise RuntimeError(str(exc)) from exc
        except SoftTimeLimitExceeded:
            db = SessionLocal()
            try:
                FailureStage.mark_screenshot_job_failed(db, session_id, "Screenshot generation timed out.")
            finally:
                db.close()
            raise
