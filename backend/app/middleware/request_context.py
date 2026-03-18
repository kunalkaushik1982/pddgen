r"""
Purpose: Bind request-scoped logging context and correlation identifiers.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\middleware\request_context.py
"""

from __future__ import annotations

import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware

from app.core.observability import bind_log_context, get_logger


logger = get_logger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach request correlation data to logs and responses."""

    async def dispatch(self, request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("X-Request-Id") or str(uuid4())
        started_at = time.perf_counter()
        with bind_log_context(
            request_id=request_id,
            http_method=request.method,
            http_path=request.url.path,
        ):
            try:
                response = await call_next(request)
            except Exception:
                duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
                logger.exception("Unhandled request error", extra={"event": "request.error", "duration_ms": duration_ms})
                raise

            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            response.headers["X-Request-Id"] = request_id
            logger.info(
                "Request completed",
                extra={
                    "event": "request.completed",
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )
            return response
