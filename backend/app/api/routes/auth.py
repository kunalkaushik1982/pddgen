r"""
Purpose: API routes for simple username/password authentication.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\api\routes\auth.py
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Response
from sqlalchemy.orm import Session

from app.api.dependencies import get_auth_service, get_current_user
from app.db.session import get_db_session
from app.models.user import UserModel
from app.schemas.auth import AuthRequest, AuthResponse, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
def register(
    payload: AuthRequest,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthResponse:
    """Create one user account and return an API token."""
    user, token = service.register(db, username=payload.username, password=payload.password)
    return AuthResponse(token=token, user=UserResponse.model_validate(user))


@router.post("/login", response_model=AuthResponse)
def login(
    payload: AuthRequest,
    db: Annotated[Session, Depends(get_db_session)],
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthResponse:
    """Authenticate one user and return an API token."""
    user, token = service.login(db, username=payload.username, password=payload.password)
    return AuthResponse(token=token, user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse)
def get_me(current_user: Annotated[UserModel, Depends(get_current_user)]) -> UserResponse:
    """Return the currently authenticated user."""
    return UserResponse.model_validate(current_user)


@router.post("/logout", status_code=204)
def logout(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    db: Annotated[Session, Depends(get_db_session)] = None,
    service: Annotated[AuthService, Depends(get_auth_service)] = None,
) -> Response:
    """Invalidate the current API token."""
    token = _extract_bearer_token(authorization)
    if token:
        service.logout(db, token=token)
    return Response(status_code=204)


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token
