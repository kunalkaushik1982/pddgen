r"""
Job messaging contracts (interface-first).

Enqueue (producer), distributed lock, and per-session run-guards (draft / screenshot)
are separate ports so brokers, stores, and dedupe/concurrency policy can be swapped
independently.
"""

from __future__ import annotations

from typing import Protocol

from app.portability.job_messaging.envelope import JobEnvelope


class EnqueueHandle(Protocol):
    """Opaque handle returned after enqueue (e.g. Celery AsyncResult)."""

    @property
    def id(self) -> str: ...


class JobEnqueuePort(Protocol):
    """Producer-side: submit a background job to a named logical queue."""

    def enqueue(self, job: JobEnvelope, *, queue: str) -> EnqueueHandle:
        """Schedule work from a versioned envelope; implementation maps to broker-specific send."""
        ...


class DistributedLockPort(Protocol):
    """Distributed mutual exclusion (Redis, DynamoDB, etc.) — independent of message broker."""

    def try_acquire(self, key: str, *, ttl_seconds: int) -> bool:
        """Return True if lock acquired (e.g. SET NX EX)."""
        ...

    def release(self, key: str) -> None:
        """Best-effort release of the lock key."""
        ...


class SessionRunGuardPort(Protocol):
    """Per-session reservation for at-most-one in-flight generation run (draft or screenshot)."""

    def try_reserve(self, session_id: str) -> bool:
        """Return True if this session may start a guarded generation run."""
        ...

    def release(self, session_id: str) -> None:
        """Release reservation after the worker finishes (success or failure)."""
        ...


ScreenshotRunGuardPort = SessionRunGuardPort
DraftRunGuardPort = SessionRunGuardPort
