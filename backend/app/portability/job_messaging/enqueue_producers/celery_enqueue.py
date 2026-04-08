r"""Celery-backed `JobEnqueuePort` (broker transport is Celery configuration, not this class)."""

from __future__ import annotations

from celery import Celery

from app.core.config import Settings
from app.portability.job_messaging.enqueue_producers.common import send_with_retry
from app.portability.job_messaging.envelope import JobEnvelope, JobType
from app.portability.job_messaging.protocols import EnqueueHandle, JobEnqueuePort


class CeleryJobEnqueueAdapter(JobEnqueuePort):
    """Delegates enqueue to a Celery application (Redis, SQS, AMQP, etc. via broker_url)."""

    __slots__ = ("_celery", "_max_retries", "_retry_backoff")

    def __init__(self, *, celery_app: Celery, max_retries: int = 0, retry_backoff_seconds: float = 0.5) -> None:
        self._celery = celery_app
        self._max_retries = max_retries
        self._retry_backoff = retry_backoff_seconds

    def enqueue(self, job: JobEnvelope, *, queue: str) -> EnqueueHandle:
        if job.job_type is JobType.DRAFT_GENERATION:
            task_name, args = "draft_generation.run", [job.session_id]
        elif job.job_type is JobType.SCREENSHOT_GENERATION:
            task_name, args = "screenshot_generation.run", [job.session_id]
        else:  # pragma: no cover
            raise AssertionError(f"Unhandled job_type: {job.job_type!r}")
        return send_with_retry(
            backend="celery",
            queue=queue,
            job=job,
            max_retries=self._max_retries,
            backoff_seconds=self._retry_backoff,
            send_once=lambda: self._celery.send_task(task_name, args=args, queue=queue),
        )

    @classmethod
    def celery_app_from_settings(cls, settings: Settings) -> Celery:
        """Shared Celery app used by the API process only for enqueue (no worker consumer here)."""
        return Celery(
            "pdd_generator_backend",
            broker=settings.redis_url,
            backend=settings.redis_url,
        )


def build_celery_app_for_enqueue(settings: Settings) -> Celery:
    """Factory for a Celery app configured from settings (producer-side)."""
    return CeleryJobEnqueueAdapter.celery_app_from_settings(settings)
