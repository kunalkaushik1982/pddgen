r"""
Purpose: Config-driven auth facade over identity providers and session services.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\auth_service.py
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.user import UserModel
from app.portability.auth_registry import build_identity_provider
from app.services.auth_types import AuthSession, IdentityProvider, SessionService
from app.services.database_session_service import DatabaseSessionService


class AuthService:
    """Coordinate configurable identity providers and session storage."""

    def __init__(
        self,
        *,
        identity_provider: IdentityProvider | None = None,
        session_service: SessionService | None = None,
    ) -> None:
        self.settings = get_settings()
        self.identity_provider = identity_provider or self._build_identity_provider()
        self.session_service = session_service or DatabaseSessionService()

    def register(self, db: Session, *, username: str, password: str) -> AuthSession:
        if not self.settings.auth_registration_enabled:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Self-service registration is disabled.")

        try:
            user = self.identity_provider.register(db, username=username, password=password)
        except NotImplementedError as error:
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(error)) from error
        token = self.session_service.create_session(db, user=user)
        db.commit()
        db.refresh(user)
        return AuthSession(user=user, session_token=token)

    def login(self, db: Session, *, username: str, password: str) -> AuthSession:
        try:
            user = self.identity_provider.authenticate(db, username=username, password=password)
        except NotImplementedError as error:
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(error)) from error
        token = self.session_service.create_session(db, user=user)
        db.commit()
        db.refresh(user)
        return AuthSession(user=user, session_token=token)

    def logout(self, db: Session, *, token: str) -> None:
        self.session_service.revoke_session(db, token=token)

    def authenticate_token(self, db: Session, *, token: str) -> UserModel:
        return self.session_service.resolve_user(db, token=token)

    def _build_identity_provider(self) -> IdentityProvider:
        return build_identity_provider(self.settings)
