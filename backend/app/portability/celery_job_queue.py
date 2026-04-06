r"""
Default Celery + Redis-backed implementation of `JobQueuePort`.

To replace the queue (e.g. SQS, RQ), implement `JobQueuePort` in a new adapter and
inject it when constructing `JobDispatcherService` from `dependencies.py`.
"""

from __future__ import annotations

from typing import Any

from celery import Celery

from app.core.config import Settings
from app.portability.contracts import JobQueuePort


class CeleryRedisJobQueue(JobQueuePort):
    """Celery app with Redis broker/backend; implements distributed lock via Redis client."""

    def __init__(self, *, celery_app: Celery, settings: Settings) -> None:
        self._celery = celery_app
        self._settings = settings

    @classmethod
    def from_settings(cls, settings: Settings) -> CeleryRedisJobQueue:
        app = Celery(
            "pdd_generator_backend",
            broker=settings.redis_url,
            backend=settings.redis_url,
        )
        return cls(celery_app=app, settings=settings)

    def send_named_task(self, task_name: str, args: list[Any], *, queue: str) -> Any:
        return self._celery.send_task(task_name, args=args, queue=queue)

    def try_acquire_lock(self, key: str, *, ttl_seconds: int) -> bool:
        backend_client = getattr(self._celery.backend, "client", None)
        if backend_client is None:
            return True
        return bool(backend_client.set(key, "1", ex=ttl_seconds, nx=True))

    def release_lock(self, key: str) -> None:
        backend_client = getattr(self._celery.backend, "client", None)
        if backend_client is None:
            return
        backend_client.delete(key)


def build_default_job_queue(settings: Settings) -> JobQueuePort:
    """Default queue implementation for production and local dev."""
    return CeleryRedisJobQueue.from_settings(settings)
