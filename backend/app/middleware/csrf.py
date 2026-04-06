r"""
Purpose: Middleware for enforcing CSRF validation on cookie-authenticated API requests.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\middleware\csrf.py
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

class CSRFMiddleware(BaseHTTPMiddleware):
    """Validate CSRF tokens for unsafe requests backed by cookie auth."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        try:
            request.app.state.csrf_service.validate_request(request)
        except Exception as error:
            if getattr(error, "status_code", None) == 403:
                return JSONResponse(status_code=403, content={"detail": str(error.detail)})
            raise
        return await call_next(request)
