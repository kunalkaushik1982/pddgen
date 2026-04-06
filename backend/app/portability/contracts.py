r"""
Stable ports (Protocols) for infrastructure that callers swap via adapters.
Business services should depend on these shapes when injected from dependencies.py.
"""

from __future__ import annotations

from typing import Any, Protocol


class TaskSendResult(Protocol):
    """Minimal task handle returned after enqueue (e.g. Celery AsyncResult)."""

    @property
    def id(self) -> str: ...


class JobQueuePort(Protocol):
    """Background job broker used by JobDispatcherService."""

    def send_named_task(self, task_name: str, args: list[Any], *, queue: str) -> TaskSendResult:
        """Enqueue a task by Celery task name and return a handle with an id."""

    def try_acquire_lock(self, key: str, *, ttl_seconds: int) -> bool:
        """Best-effort distributed lock (e.g. Redis SET NX EX). Return True if acquired."""

    def release_lock(self, key: str) -> None:
        """Release a lock key if present."""
