r"""
Purpose: CSRF token issuance and validation for cookie-authenticated requests.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\csrf_service.py
"""

import hmac
import secrets

from fastapi import HTTPException, Request, Response, status

from app.core.config import Settings


class CsrfService:
    """Issue and validate CSRF tokens using the double-submit cookie pattern."""

    def __init__(self, *, settings: Settings) -> None:
        self.settings = settings

    def issue_token(self) -> str:
        return secrets.token_urlsafe(32)

    def set_cookie(self, response: Response, token: str) -> None:
        response.set_cookie(
            key=self.settings.auth_csrf_cookie_name,
            value=token,
            httponly=False,
            secure=self.settings.auth_cookie_secure,
            samesite=self.settings.auth_cookie_samesite,
            domain=self.settings.auth_cookie_domain,
            max_age=self.settings.auth_token_days * 24 * 60 * 60,
            path="/",
        )

    def clear_cookie(self, response: Response) -> None:
        response.delete_cookie(
            key=self.settings.auth_csrf_cookie_name,
            secure=self.settings.auth_cookie_secure,
            samesite=self.settings.auth_cookie_samesite,
            domain=self.settings.auth_cookie_domain,
            path="/",
        )

    def validate_request(self, request: Request) -> None:
        if not self.settings.auth_csrf_protection_enabled:
            return
        if request.method.upper() in {"GET", "HEAD", "OPTIONS"}:
            return
        if not request.url.path.startswith(self.settings.api_prefix):
            return

        # Password reset is used without an authenticated session; allow even if a stale session cookie exists.
        if request.url.path in (
            f"{self.settings.api_prefix}/auth/password-reset/request",
            f"{self.settings.api_prefix}/auth/password-reset/confirm",
        ):
            return

        # Payment provider webhooks use signature verification instead of CSRF tokens.
        if request.url.path.startswith(f"{self.settings.api_prefix}/payments/webhooks"):
            return

        session_token = request.cookies.get(self.settings.auth_cookie_name)
        if not session_token:
            return

        cookie_token = request.cookies.get(self.settings.auth_csrf_cookie_name)
        header_token = request.headers.get(self.settings.auth_csrf_header_name)
        if not cookie_token or not header_token or not hmac.compare_digest(cookie_token, header_token):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed.")
