r"""Shared producer helpers: queue target resolution, observability, and retry wrapper."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

from app.core.observability import get_logger
from app.portability.job_messaging.envelope import JobEnvelope

logger = get_logger(__name__)

T = TypeVar("T")


class JobEnqueueError(RuntimeError):
    """Normalized producer error raised after retry exhaustion."""


def resolve_target_for_queue(
    *,
    queue: str,
    mapping: dict[str, str],
    fallback: str,
    target_name: str,
) -> str:
    """Resolve logical queue name to backend target with mapping-first, fallback-second policy."""
    if queue in mapping:
        target = mapping[queue].strip()
        if target:
            return target
    if fallback.strip():
        return fallback.strip()
    raise ValueError(
        f"No {target_name} configured for logical queue {queue!r}. "
        f"Provide a mapping entry or set the default {target_name} setting."
    )


def send_with_retry(
    *,
    backend: str,
    queue: str,
    job: JobEnvelope,
    max_retries: int,
    backoff_seconds: float,
    send_once: Callable[[], T],
) -> T:
    """Send once with standardized logging and bounded retry."""
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            result = send_once()
            logger.info(
                "Job enqueue succeeded",
                extra={
                    "event": "job_enqueue.succeeded",
                    "backend": backend,
                    "logical_queue": queue,
                    "job_type": job.job_type.value,
                    "session_id": job.session_id,
                    "attempt": attempt + 1,
                },
            )
            return result
        except Exception as exc:  # pragma: no cover - branch behavior validated in adapter tests
            last_error = exc
            final_attempt = attempt >= max_retries
            logger.warning(
                "Job enqueue failed",
                extra={
                    "event": "job_enqueue.failed",
                    "backend": backend,
                    "logical_queue": queue,
                    "job_type": job.job_type.value,
                    "session_id": job.session_id,
                    "attempt": attempt + 1,
                    "will_retry": not final_attempt,
                    "error_type": type(exc).__name__,
                },
            )
            if final_attempt:
                break
            sleep_for = max(0.0, backoff_seconds) * (2**attempt)
            if sleep_for > 0:
                time.sleep(sleep_for)
    raise JobEnqueueError(f"Enqueue failed for backend={backend!r}, queue={queue!r}") from last_error
