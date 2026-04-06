r"""Screenshot run reservation using a `DistributedLockPort` (pluggable dedupe / concurrency)."""

from __future__ import annotations

from app.core.config import Settings
from app.portability.job_messaging.protocols import DistributedLockPort, ScreenshotRunGuardPort


class ScreenshotLockRunGuardAdapter(ScreenshotRunGuardPort):
    """Default: one in-flight screenshot job per session via TTL lock keys."""

    __slots__ = ("_lock", "_ttl_seconds", "_key_prefix")

    def __init__(
        self,
        *,
        lock: DistributedLockPort,
        ttl_seconds: int,
        key_prefix: str = "pdd-generator:screenshot-generation-lock",
    ) -> None:
        self._lock = lock
        self._ttl_seconds = ttl_seconds
        self._key_prefix = key_prefix

    def _key(self, session_id: str) -> str:
        return f"{self._key_prefix}:{session_id}"

    def try_reserve(self, session_id: str) -> bool:
        return self._lock.try_acquire(self._key(session_id), ttl_seconds=self._ttl_seconds)

    def release(self, session_id: str) -> None:
        self._lock.release(self._key(session_id))


def build_screenshot_run_guard(settings: Settings, *, lock: DistributedLockPort) -> ScreenshotRunGuardPort:
    return ScreenshotLockRunGuardAdapter(lock=lock, ttl_seconds=settings.screenshot_generation_lock_seconds)
