r"""
Purpose: API routes for simple username/password authentication.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\api\routes\auth.py
"""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.api.dependencies import get_auth_service, get_current_user
from app.db.session import get_db_session
from app.models.user import UserModel
from app.schemas.auth import AuthRequest, AuthResponse, UserResponse
from app.services.auth_service import AuthService
from app.services.csrf_service import CsrfService

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()
csrf_service = CsrfService(settings)


@router.post("/register", response_model=AuthResponse)
def register(
    payload: AuthRequest,
    response: Response,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthResponse:
    """Create one user account and establish an authenticated session."""
    auth_session = service.register(db, username=payload.username, password=payload.password)
    _set_auth_cookie(response, auth_session.session_token)
    _set_csrf_cookie(response)
    return AuthResponse(
        auth_status=auth_session.status,
        challenge_type=auth_session.challenge_type,
        challenge_token=auth_session.challenge_token,
        user=_build_user_response(auth_session.user),
    )


@router.post("/login", response_model=AuthResponse)
def login(
    payload: AuthRequest,
    response: Response,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthResponse:
    """Authenticate one user and establish an authenticated session."""
    auth_session = service.login(db, username=payload.username, password=payload.password)
    _set_auth_cookie(response, auth_session.session_token)
    _set_csrf_cookie(response)
    return AuthResponse(
        auth_status=auth_session.status,
        challenge_type=auth_session.challenge_type,
        challenge_token=auth_session.challenge_token,
        user=_build_user_response(auth_session.user),
    )


@router.get("/me", response_model=UserResponse)
def get_me(
    response: Response,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    csrf_cookie: Annotated[str | None, Cookie(alias=settings.auth_csrf_cookie_name)] = None,
) -> UserResponse:
    """Return the currently authenticated user."""
    if not csrf_cookie:
        _set_csrf_cookie(response)
    return _build_user_response(current_user)


@router.post("/logout", status_code=204)
def logout(
    session_cookie: Annotated[str | None, Cookie(alias=settings.auth_cookie_name)] = None,
    db: Annotated[Session, Depends(get_db_session)] = None,
    service: Annotated[AuthService, Depends(get_auth_service)] = None,
    response: Response = None,
) -> Response:
    """Invalidate the current authenticated session."""
    token = session_cookie
    if token:
        service.logout(db, token=token)
    cleared_response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_auth_cookie(cleared_response)
    _clear_csrf_cookie(cleared_response)
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


def _set_csrf_cookie(response: Response) -> None:
    csrf_service.set_cookie(response, csrf_service.issue_token())


def _clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.auth_cookie_name,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        domain=settings.auth_cookie_domain,
        path="/",
    )


def _clear_csrf_cookie(response: Response) -> None:
    csrf_service.clear_cookie(response)


def _build_user_response(user: UserModel) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        created_at=user.created_at,
        is_admin=user.username in settings.admin_usernames,
    )
