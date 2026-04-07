r"""Compose default messaging adapters from `Settings` (plug-and-play wiring root)."""

from __future__ import annotations

import importlib
from collections.abc import Callable
from functools import lru_cache

from app.core.config import Settings
from app.portability.job_messaging.protocols import (
    DistributedLockPort,
    DraftRunGuardPort,
    JobEnqueuePort,
    ScreenshotRunGuardPort,
)
from app.portability.job_messaging.locks.redis_lock import build_redis_distributed_lock
from app.portability.job_messaging.run_guards.session_run_guard import build_draft_run_guard, build_screenshot_run_guard


def _build_celery_enqueue(settings: Settings) -> JobEnqueuePort:
    from app.portability.job_messaging.enqueue_producers.celery_enqueue import CeleryJobEnqueueAdapter, build_celery_app_for_enqueue

    app = build_celery_app_for_enqueue(settings)
    return CeleryJobEnqueueAdapter(
        celery_app=app,
        max_retries=settings.job_enqueue_max_retries,
        retry_backoff_seconds=settings.job_enqueue_retry_backoff_seconds,
    )


def _build_sqs_enqueue(settings: Settings) -> JobEnqueuePort:
    from app.portability.job_messaging.enqueue_producers.sqs_enqueue import SqsJobEnqueueAdapter

    return SqsJobEnqueueAdapter(settings=settings)


def _build_azure_service_bus_enqueue(settings: Settings) -> JobEnqueuePort:
    from app.portability.job_messaging.enqueue_producers.azure_service_bus_enqueue import AzureServiceBusJobEnqueueAdapter

    return AzureServiceBusJobEnqueueAdapter(settings=settings)


def _build_gcp_pubsub_enqueue(settings: Settings) -> JobEnqueuePort:
    from app.portability.job_messaging.enqueue_producers.gcp_pubsub_enqueue import GcpPubSubJobEnqueueAdapter

    return GcpPubSubJobEnqueueAdapter(settings=settings)


_ENQUEUE_BACKEND_BUILDERS: dict[str, Callable[[Settings], JobEnqueuePort]] = {
    "celery": _build_celery_enqueue,
    "sqs": _build_sqs_enqueue,
    "azure_service_bus": _build_azure_service_bus_enqueue,
    "gcp_pubsub": _build_gcp_pubsub_enqueue,
}


@lru_cache(maxsize=16)
def _load_enqueue_factory_callable(factory: str) -> Callable[[Settings], JobEnqueuePort]:
    """Resolve ``module.path:callable`` to a ``(Settings) -> JobEnqueuePort`` builder (cached)."""
    if factory.count(":") != 1:
        raise ValueError("job_enqueue_factory must be exactly 'module.path:callable'")
    module_path, attr = factory.split(":", 1)
    module_path, attr = module_path.strip(), attr.strip()
    if not module_path or not attr:
        raise ValueError("job_enqueue_factory must be exactly 'module.path:callable'")
    module = importlib.import_module(module_path)
    fn = getattr(module, attr, None)
    if fn is None:
        raise ValueError(f"job_enqueue_factory: {factory!r} — attribute {attr!r} not found on module {module_path!r}")
    if not callable(fn):
        raise TypeError(f"job_enqueue_factory: {factory!r} must name a callable, got {type(fn).__name__}")
    return fn  # type: ignore[return-value]


def build_job_enqueue_port(settings: Settings) -> JobEnqueuePort:
    """Factory for producer-side enqueue: optional plug-in factory, else ``job_enqueue_backend`` registry."""
    factory = settings.job_enqueue_factory.strip()
    if factory:
        builder = _load_enqueue_factory_callable(factory)
        return builder(settings)
    backend = settings.job_enqueue_backend.strip().lower()
    builder = _ENQUEUE_BACKEND_BUILDERS.get(backend)
    if builder is None:
        raise ValueError(f"Unknown job_enqueue_backend: {backend!r}")
    return builder(settings)


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
