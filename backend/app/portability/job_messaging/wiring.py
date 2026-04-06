r"""Compose default messaging adapters from `Settings` (plug-and-play wiring root)."""

from __future__ import annotations

from app.core.config import Settings
from app.portability.job_messaging.celery_enqueue_adapter import CeleryJobEnqueueAdapter, build_celery_app_for_enqueue
from app.portability.job_messaging.protocols import (
    DistributedLockPort,
    DraftRunGuardPort,
    JobEnqueuePort,
    ScreenshotRunGuardPort,
)
from app.portability.job_messaging.redis_lock_adapter import build_redis_distributed_lock
from app.portability.job_messaging.screenshot_guard_adapter import build_draft_run_guard, build_screenshot_run_guard
from app.portability.job_messaging.sqs_enqueue_adapter import SqsJobEnqueueAdapter


def build_job_enqueue_port(settings: Settings) -> JobEnqueuePort:
    """Factory for producer-side enqueue (Celery, SQS, …) from ``job_enqueue_backend``."""
    backend = settings.job_enqueue_backend.strip().lower()
    if backend == "celery":
        app = build_celery_app_for_enqueue(settings)
        return CeleryJobEnqueueAdapter(celery_app=app)
    if backend == "sqs":
        return SqsJobEnqueueAdapter(settings=settings)
    raise ValueError(f"Unknown job_enqueue_backend: {backend!r}")


def build_default_job_enqueue_port(settings: Settings) -> JobEnqueuePort:
    """Backward-compatible alias for :func:`build_job_enqueue_port`."""
    return build_job_enqueue_port(settings)


def build_default_distributed_lock(settings: Settings) -> DistributedLockPort:
    return build_redis_distributed_lock(settings)


def build_default_screenshot_run_guard(settings: Settings) -> ScreenshotRunGuardPort:
    lock = build_default_distributed_lock(settings)
    return build_screenshot_run_guard(settings, lock=lock)


def build_default_draft_run_guard(settings: Settings) -> DraftRunGuardPort:
    lock = build_default_distributed_lock(settings)
    return build_draft_run_guard(settings, lock=lock)
