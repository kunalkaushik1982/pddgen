r"""
Purpose: Background task for long-running draft generation work.
Full filepath: C:\Users\work\Documents\PddGenerator\worker\tasks\draft_generation.py
"""

import time

from celery.exceptions import SoftTimeLimitExceeded

from worker import bootstrap as _bootstrap  # noqa: F401
from app.core.observability import bind_log_context, get_logger
from app.db.session import SessionLocal
from app.services.platform.generation_timing import track_draft_generation_wall_time
from worker.bootstrap import get_backend_settings
from worker.celery_app import celery_app
from worker.pipeline.stages.failure import FailureStage
from worker.pipeline.stages.worker import DraftGenerationWorker

logger = get_logger(__name__)

_limits = get_backend_settings()


@celery_app.task(
    name="draft_generation.run",
    bind=True,
    autoretry_for=(RuntimeError,),
    retry_backoff=True,
    max_retries=3,
    soft_time_limit=_limits.draft_celery_soft_time_limit_seconds,
    time_limit=_limits.draft_celery_time_limit_seconds,
)
def run_draft_generation(self, session_id: str) -> dict[str, int | str]:
    """Run the draft generation pipeline in the background."""
    with bind_log_context(task_id=self.request.id, session_id=session_id):
        logger.info("Draft generation task started", extra={"event": "draft_generation.task_started"})
        try:
            with track_draft_generation_wall_time(session_id):
                worker = DraftGenerationWorker(task_id=self.request.id)
                try:
                    started = time.monotonic()
                    result = worker.run(session_id)
                    duration_s = round(time.monotonic() - started, 3)
                    logger.info(
                        "Draft generation task completed",
                        extra={
                            "event": "draft_generation.task_completed",
                            "duration_seconds": duration_s,
                            "duration_ms": int(duration_s * 1000),
                        },
                    )
                    from app.services.admin.usage_metrics_service import persist_background_job_run

                    persist_background_job_run(
                        session_id=session_id,
                        job_type="draft_generation",
                        celery_task_id=self.request.id,
                        duration_seconds=duration_s,
                    )
                    return result
                except ValueError as exc:
                    logger.exception("Draft generation task failed", extra={"event": "draft_generation.task_failed"})
                    raise RuntimeError(str(exc)) from exc
        except SoftTimeLimitExceeded:
            db = SessionLocal()
            try:
                FailureStage.mark_failed(db, session_id, "Draft generation timed out.")
            finally:
                db.close()
            raise
