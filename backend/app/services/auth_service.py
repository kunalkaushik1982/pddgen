r"""
Purpose: Config-driven auth facade over identity providers and session services.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\auth_service.py
"""

from datetime import datetime, timedelta, timezone
import hashlib
import logging
import secrets

from fastapi import HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.user import UserModel
from app.models.user_email_verification_token import UserEmailVerificationTokenModel
from app.models.user_password_reset_token import UserPasswordResetTokenModel
from app.services.outbound_email import (
    send_email_verification_message,
    send_password_reset_message,
    smtp_configured,
)
from app.services.password_identity_provider import PasswordIdentityProvider
from app.services.auth_types import AuthSession, IdentityProvider, SessionService

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


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

    def register(self, db: Session, *, username: str, password: str, email: str) -> AuthSession:
        if not self.settings.auth_registration_enabled:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Self-service registration is disabled.")

        try:
            user = self.identity_provider.register(db, username=username, password=password, email=email)
        except NotImplementedError as error:
            raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(error)) from error

        if smtp_configured(self.settings):
            self._issue_email_verification(db, user=user)
        else:
            user.email_verified_at = datetime.utcnow()
        db.flush()

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

    def verify_email_with_token(self, db: Session, *, token: str) -> None:
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        row = db.execute(
            select(UserEmailVerificationTokenModel).where(UserEmailVerificationTokenModel.token_hash == token_hash)
        ).scalar_one_or_none()
        if row is None or row.used_at is not None or _as_utc(row.expires_at) < _utc_now():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification link.")
        user = db.execute(select(UserModel).where(UserModel.id == row.user_id)).scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification link.")
        user.email_verified_at = datetime.utcnow()
        row.used_at = datetime.utcnow()
        db.commit()

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
        # Prefer matching by verified email to avoid duplicate-email collisions.
        user = db.execute(select(UserModel).where(UserModel.email == email)).scalar_one_or_none()
        if user is None:
            user = db.execute(select(UserModel).where(UserModel.username == email)).scalar_one_or_none()
        if user is None:
            if not self.settings.auth_google_auto_create_user:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Google sign-up is disabled.")
            user = UserModel(
                username=email,
                email=email,
                email_verified_at=datetime.utcnow(),
                password_hash=PasswordIdentityProvider._hash_password(secrets.token_urlsafe(48)),
            )
            db.add(user)
            db.flush()
        else:
            if user.email is None:
                user.email = email
            elif user.email != email:
                # Keep existing account boundaries explicit instead of hitting DB unique-email violations.
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Google account email is already linked to another user.",
                )
            if user.email_verified_at is None:
                user.email_verified_at = datetime.utcnow()
        token = self.session_service.create_session(db, user=user)
        db.commit()
        db.refresh(user)
        return AuthSession(user=user, session_token=token)

    def request_password_reset(self, db: Session, *, email: str) -> str | None:
        if not self.settings.auth_password_reset_enabled:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Password reset is disabled.")
        normalized = email.strip().lower()
        if not normalized:
            return None
        user = db.execute(select(UserModel).where(UserModel.email == normalized)).scalar_one_or_none()
        if user is None or user.email_verified_at is None:
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
        db.flush()

        if smtp_configured(self.settings):
            base = self.settings.auth_public_app_url.rstrip("/")
            reset_url = f"{base}/auth/reset-password?token={raw_token}"
            try:
                send_password_reset_message(
                    settings=self.settings,
                    to_email=user.email or normalized,
                    reset_url=reset_url,
                    app_name=self.settings.app_name,
                )
            except Exception as exc:
                logger.exception("Password reset email failed")
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Could not send password reset email. Try again later.",
                ) from exc
            db.commit()
            return None

        if self.settings.auth_password_reset_return_token_in_response or self.settings.app_debug:
            db.commit()
            return raw_token
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email delivery is not configured. Set SMTP (smtp_host) or enable debug token return for development.",
        )

    def confirm_password_reset(self, db: Session, *, token: str, new_password: str) -> None:
        if not self.settings.auth_password_reset_enabled:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Password reset is disabled.")
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        reset = db.execute(
            select(UserPasswordResetTokenModel).where(UserPasswordResetTokenModel.token_hash == token_hash)
        ).scalar_one_or_none()
        if reset is None or reset.used_at is not None or _as_utc(reset.expires_at) < _utc_now():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token.")
        user = db.execute(select(UserModel).where(UserModel.id == reset.user_id)).scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset token user.")
        user.password_hash = PasswordIdentityProvider._hash_password(new_password)
        reset.used_at = datetime.utcnow()
        db.commit()

    def _issue_email_verification(self, db: Session, *, user: UserModel) -> None:
        if not user.email:
            return
        raw = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        expires_at = datetime.utcnow() + timedelta(minutes=self.settings.auth_email_verification_token_ttl_minutes)
        db.add(
            UserEmailVerificationTokenModel(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=expires_at,
            )
        )
        db.flush()
        base = self.settings.auth_api_public_base_url.rstrip("/")
        verify_url = f"{base}/api/auth/verify-email?token={raw}"
        try:
            send_email_verification_message(
                settings=self.settings,
                to_email=user.email,
                verify_url=verify_url,
                app_name=self.settings.app_name,
            )
        except Exception as exc:
            logger.exception("Verification email failed")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not send verification email. Check SMTP settings or try again later.",
            ) from exc
