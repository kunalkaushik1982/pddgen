r"""
Purpose: API routes for simple username/password authentication.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\api\routes\auth.py
"""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.api.dependencies import get_auth_service, get_csrf_service
from app.db.session import get_db_session
from app.models.user import UserModel
from app.schemas.auth import (
    AuthRequest,
    AuthResponse,
    GoogleAuthRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    PasswordResetRequestResponse,
    RegisterRequest,
    UserResponse,
)
from app.services.auth.auth_service import AuthService
from app.services.platform.csrf_service import CsrfService

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/register", response_model=AuthResponse)
def register(
    payload: RegisterRequest,
    response: Response,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[AuthService, Depends(get_auth_service)],
    csrf: Annotated[CsrfService, Depends(get_csrf_service)],
) -> AuthResponse:
    """Create one user account and establish an authenticated session."""
    auth_session = service.register(
        db,
        username=payload.username,
        password=payload.password,
        email=payload.email,
    )
    _set_auth_cookie(response, auth_session.session_token)
    _set_csrf_cookie(response, csrf)
    return AuthResponse(
        auth_status=auth_session.status,
        challenge_type=auth_session.challenge_type,
        challenge_token=auth_session.challenge_token,
        user=_build_user_response(auth_session.user),
    )


@router.get("/verify-email")
def verify_email(
    token: str,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> RedirectResponse:
    """Consume email verification link and redirect to the SPA sign-in page."""
    service.verify_email_with_token(db, token=token)
    return RedirectResponse(
        url=f"{settings.auth_public_app_url.rstrip('/')}/auth?email_verified=1",
        status_code=status.HTTP_302_FOUND,
    )


@router.post("/login", response_model=AuthResponse)
def login(
    payload: AuthRequest,
    response: Response,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[AuthService, Depends(get_auth_service)],
    csrf: Annotated[CsrfService, Depends(get_csrf_service)],
) -> AuthResponse:
    """Authenticate one user and establish an authenticated session."""
    auth_session = service.login(db, username=payload.username, password=payload.password)
    _set_auth_cookie(response, auth_session.session_token)
    _set_csrf_cookie(response, csrf)
    return AuthResponse(
        auth_status=auth_session.status,
        challenge_type=auth_session.challenge_type,
        challenge_token=auth_session.challenge_token,
        user=_build_user_response(auth_session.user),
    )


@router.post("/google", response_model=AuthResponse)
def login_with_google(
    payload: GoogleAuthRequest,
    response: Response,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[AuthService, Depends(get_auth_service)],
    csrf: Annotated[CsrfService, Depends(get_csrf_service)],
) -> AuthResponse:
    """Authenticate via Google token(s) and establish an authenticated session."""
    auth_session = service.login_with_google(
        db,
        id_token=payload.id_token,
        access_token=payload.access_token,
    )
    _set_auth_cookie(response, auth_session.session_token)
    _set_csrf_cookie(response, csrf)
    return AuthResponse(
        auth_status=auth_session.status,
        challenge_type=auth_session.challenge_type,
        challenge_token=auth_session.challenge_token,
        user=_build_user_response(auth_session.user),
    )


@router.post("/password-reset/request", response_model=PasswordResetRequestResponse)
def request_password_reset(
    payload: PasswordResetRequest,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> PasswordResetRequestResponse:
    """Create one-time password reset token and email a link when SMTP is configured."""
    token = service.request_password_reset(db, email=payload.email)
    return PasswordResetRequestResponse(accepted=True, reset_token=token)


@router.post("/password-reset/confirm", status_code=204)
def confirm_password_reset(
    payload: PasswordResetConfirmRequest,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> Response:
    """Reset a user's password using a valid one-time token."""
    service.confirm_password_reset(db, token=payload.token, new_password=payload.new_password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserResponse | None)
def get_me(
    response: Response,
    csrf: Annotated[CsrfService, Depends(get_csrf_service)],
    session_cookie: Annotated[str | None, Cookie(alias=settings.auth_cookie_name)] = None,
    db: Annotated[Session, Depends(get_db_session)] = None,
    service: Annotated[AuthService, Depends(get_auth_service)] = None,
    csrf_cookie: Annotated[str | None, Cookie(alias=settings.auth_csrf_cookie_name)] = None,
) -> UserResponse | None:
    """Return the currently authenticated user."""
    if not csrf_cookie:
        _set_csrf_cookie(response, csrf)
    if not session_cookie:
        return None
    try:
        current_user = service.authenticate_token(db, token=session_cookie)
    except HTTPException as error:
        if error.status_code == status.HTTP_401_UNAUTHORIZED:
            return None
        raise
    return _build_user_response(current_user)


@router.post("/logout", status_code=204)
def logout(
    csrf: Annotated[CsrfService, Depends(get_csrf_service)],
    session_cookie: Annotated[str | None, Cookie(alias=settings.auth_cookie_name)] = None,
    db: Annotated[Session, Depends(get_db_session)] = None,
    service: Annotated[AuthService, Depends(get_auth_service)] = None,
) -> Response:
    """Invalidate the current authenticated session."""
    token = session_cookie
    if token:
        service.logout(db, token=token)
    cleared_response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_auth_cookie(cleared_response)
    _clear_csrf_cookie(cleared_response, csrf)
    return cleared_response


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        domain=settings.auth_cookie_domain,
        max_age=settings.auth_token_days * 24 * 60 * 60,
        path="/",
    )


def _set_csrf_cookie(response: Response, csrf: CsrfService) -> None:
    csrf.set_cookie(response, csrf.issue_token())


def _clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.auth_cookie_name,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        domain=settings.auth_cookie_domain,
        path="/",
    )


def _clear_csrf_cookie(response: Response, csrf: CsrfService) -> None:
    csrf.clear_cookie(response)


def _build_user_response(user: UserModel) -> UserResponse:
    effective_lifetime_cap = int(settings.user_quota_lifetime_jobs) + int(user.quota_lifetime_bonus or 0)
    effective_daily_cap = int(settings.user_quota_daily_jobs) + int(user.quota_daily_bonus or 0)
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        email_verified=user.email_verified_at is not None,
        created_at=user.created_at,
        is_admin=user.username in settings.admin_usernames,
        admin_console_only=user.admin_console_only,
        billing_gstin=user.billing_gstin,
        billing_legal_name=user.billing_legal_name,
        billing_state_code=user.billing_state_code,
        quota_lifetime_bonus=int(user.quota_lifetime_bonus or 0),
        quota_daily_bonus=int(user.quota_daily_bonus or 0),
        job_usage_lifetime=int(user.job_usage_lifetime or 0),
        job_usage_daily=int(user.job_usage_daily or 0),
        effective_lifetime_cap=max(0, effective_lifetime_cap),
        effective_daily_cap=max(0, effective_daily_cap),
    )
