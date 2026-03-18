r"""
Purpose: Middleware for enforcing CSRF validation on cookie-authenticated API requests.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\middleware\csrf.py
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.csrf_service import CsrfService


class CSRFMiddleware(BaseHTTPMiddleware):
    """Validate CSRF tokens for unsafe requests backed by cookie auth."""

    def __init__(self, app) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self.csrf_service = CsrfService()

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        try:
            self.csrf_service.validate_request(request)
        except Exception as error:
            if getattr(error, "status_code", None) == 403:
                return JSONResponse(status_code=403, content={"detail": str(error.detail)})
            raise
        return await call_next(request)
