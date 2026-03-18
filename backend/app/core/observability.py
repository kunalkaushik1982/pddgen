r"""
Purpose: Shared structured logging and context propagation utilities.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\core\observability.py
"""

from __future__ import annotations

import json
import logging
from contextlib import contextmanager
from contextvars import ContextVar, Token
from datetime import datetime, timezone
from typing import Any


_LOG_CONTEXT: ContextVar[dict[str, Any]] = ContextVar("log_context", default={})
_OBSERVABILITY_CONFIGURED = False

_RESERVED_LOG_RECORD_FIELDS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}


class StructuredJsonFormatter(logging.Formatter):
    """Emit structured JSON logs with shared request/task context."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update(get_log_context())

        for key, value in record.__dict__.items():
            if key in _RESERVED_LOG_RECORD_FIELDS or key.startswith("_"):
                continue
            payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging once for backend and worker processes."""
    global _OBSERVABILITY_CONFIGURED
    if _OBSERVABILITY_CONFIGURED:
        return

    handler = logging.StreamHandler()
    handler.setFormatter(StructuredJsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level.upper())
    root_logger.addHandler(handler)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "celery", "celery.app.trace"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.propagate = True
        logger.setLevel(level.upper())

    _OBSERVABILITY_CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a module logger."""
    return logging.getLogger(name)


def get_log_context() -> dict[str, Any]:
    """Return the current structured log context."""
    return dict(_LOG_CONTEXT.get())


def set_log_context(**values: Any) -> Token[dict[str, Any]]:
    """Overlay values onto the current log context and return a reset token."""
    current = get_log_context()
    current.update({key: value for key, value in values.items() if value is not None})
    return _LOG_CONTEXT.set(current)


def reset_log_context(token: Token[dict[str, Any]]) -> None:
    """Reset the logging context to a previous token."""
    _LOG_CONTEXT.reset(token)


@contextmanager
def bind_log_context(**values: Any):
    """Temporarily bind structured logging context."""
    token = set_log_context(**values)
    try:
        yield
    finally:
        reset_log_context(token)
