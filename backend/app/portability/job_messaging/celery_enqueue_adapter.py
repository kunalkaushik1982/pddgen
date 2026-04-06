r"""Celery-backed `JobEnqueuePort` (broker transport is Celery configuration, not this class)."""

from __future__ import annotations

from typing import Any

from celery import Celery

from app.core.config import Settings
from app.portability.job_messaging.protocols import EnqueueHandle, JobEnqueuePort


class CeleryJobEnqueueAdapter(JobEnqueuePort):
    """Delegates enqueue to a Celery application (Redis, SQS, AMQP, etc. via broker_url)."""

    __slots__ = ("_celery",)

    def __init__(self, *, celery_app: Celery) -> None:
        self._celery = celery_app

    def enqueue(self, task_name: str, args: list[Any], *, queue: str) -> EnqueueHandle:
        return self._celery.send_task(task_name, args=args, queue=queue)

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
