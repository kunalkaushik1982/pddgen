r"""
Purpose: Config-driven auth facade over identity providers and session services.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\auth_service.py
"""

from datetime import datetime, timedelta
import hashlib
import secrets

from fastapi import HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.user import UserModel
from app.models.user_password_reset_token import UserPasswordResetTokenModel
from app.services.password_identity_provider import PasswordIdentityProvider
from app.services.auth_types import AuthSession, IdentityProvider, SessionService


class AuthService:
    """Coordinate configurable identity providers and session storage."""

    def __init__(
        self,
        *,
        identity_provider: IdentityProvider,
        session_service: SessionService,
    ) -> None:
        self.settings = get_settings()
        self.identity_provider = identity_provider
        self.session_service = session_service

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

    def login_with_google(self, db: Session, *, id_token: str | None = None, access_token: str | None = None) -> AuthSession:
        if not self.settings.auth_google_enabled:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Google sign-in is disabled.")
        if not id_token and not access_token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide id_token or access_token.")
        payload: dict[str, object]
        if id_token:
            client_id = self.settings.auth_google_client_id.strip()
            try:
                payload = dict(
                    google_id_token.verify_oauth2_token(
                        id_token,
                        google_requests.Request(),
                        audience=client_id,
                    )
                )
            except Exception as error:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google ID token.") from error
        else:
            assert access_token is not None
            try:
                with httpx.Client(timeout=10.0) as client:
                    response = client.get(
                        "https://openidconnect.googleapis.com/v1/userinfo",
                        headers={"Authorization": f"Bearer {access_token}"},
                    )
                response.raise_for_status()
                payload = dict(response.json())
            except Exception as error:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google access token.") from error
        email = str(payload.get("email") or "").strip().lower()
        email_verified = payload.get("email_verified")
        if isinstance(email_verified, str):
            email_verified_bool = email_verified.lower() == "true"
        else:
            email_verified_bool = bool(email_verified)
        if not email or not email_verified_bool:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google account email is not verified.")
        user = db.execute(select(UserModel).where(UserModel.username == email)).scalar_one_or_none()
        if user is None:
            if not self.settings.auth_google_auto_create_user:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Google sign-up is disabled.")
            user = UserModel(
                username=email,
                # Unused for Google logins, but required by schema.
                password_hash=PasswordIdentityProvider._hash_password(secrets.token_urlsafe(48)),
            )
            db.add(user)
            db.flush()
        token = self.session_service.create_session(db, user=user)
        db.commit()
        db.refresh(user)
        return AuthSession(user=user, session_token=token)

    def request_password_reset(self, db: Session, *, username: str) -> str | None:
        if not self.settings.auth_password_reset_enabled:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Password reset is disabled.")
        normalized = username.strip().lower()
        user = db.execute(select(UserModel).where(UserModel.username == normalized)).scalar_one_or_none()
        if user is None:
            return None
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        expires_at = datetime.utcnow() + timedelta(minutes=self.settings.auth_password_reset_token_ttl_minutes)
        db.add(
            UserPasswordResetTokenModel(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=expires_at,
            )
        )
        db.commit()
        if self.settings.auth_password_reset_return_token_in_response or self.settings.app_debug:
            return raw_token
        return None

    def confirm_password_reset(self, db: Session, *, token: str, new_password: str) -> None:
        if not self.settings.auth_password_reset_enabled:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Password reset is disabled.")
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        reset = db.execute(
            select(UserPasswordResetTokenModel).where(UserPasswordResetTokenModel.token_hash == token_hash)
        ).scalar_one_or_none()
        if reset is None or reset.used_at is not None or reset.expires_at < datetime.utcnow():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token.")
        user = db.execute(select(UserModel).where(UserModel.id == reset.user_id)).scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset token user.")
        user.password_hash = PasswordIdentityProvider._hash_password(new_password)
        reset.used_at = datetime.utcnow()
        db.commit()
