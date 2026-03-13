r"""
Purpose: Simple username/password auth service with token-backed API sessions.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\auth_service.py
"""

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.user import UserModel
from app.models.user_auth_token import UserAuthTokenModel


class AuthService:
    """Manage user registration, login, and token resolution."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def register(self, db: Session, *, username: str, password: str) -> tuple[UserModel, str]:
        normalized_username = username.strip()
        existing = db.execute(select(UserModel).where(UserModel.username == normalized_username)).scalar_one_or_none()
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists.")

        user = UserModel(
            username=normalized_username,
            password_hash=self._hash_password(password),
        )
        db.add(user)
        db.flush()
        token = self._create_token(db, user)
        db.commit()
        db.refresh(user)
        return user, token

    def login(self, db: Session, *, username: str, password: str) -> tuple[UserModel, str]:
        normalized_username = username.strip()
        user = db.execute(select(UserModel).where(UserModel.username == normalized_username)).scalar_one_or_none()
        if user is None or not self._verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password.")

        token = self._create_token(db, user)
        db.commit()
        db.refresh(user)
        return user, token

    def logout(self, db: Session, *, token: str) -> None:
        record = db.execute(
            select(UserAuthTokenModel).where(UserAuthTokenModel.token_hash == self._hash_token(token))
        ).scalar_one_or_none()
        if record is None:
            return
        db.delete(record)
        db.commit()

    def authenticate_token(self, db: Session, *, token: str) -> UserModel:
        record = db.execute(
            select(UserAuthTokenModel).where(UserAuthTokenModel.token_hash == self._hash_token(token))
        ).scalar_one_or_none()
        if record is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

        current_time = datetime.now(record.expires_at.tzinfo) if record.expires_at.tzinfo else datetime.now(timezone.utc).replace(tzinfo=None)
        if record.expires_at < current_time:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
        return record.user

    def _create_token(self, db: Session, user: UserModel) -> str:
        raw_token = secrets.token_urlsafe(32)
        db.add(
            UserAuthTokenModel(
                user_id=user.id,
                token_hash=self._hash_token(raw_token),
                expires_at=datetime.utcnow() + timedelta(days=self.settings.auth_token_days),
            )
        )
        return raw_token

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _hash_password(password: str) -> str:
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
        return f"{salt.hex()}:{digest.hex()}"

    @staticmethod
    def _verify_password(password: str, stored_hash: str) -> bool:
        try:
            salt_hex, digest_hex = stored_hash.split(":", maxsplit=1)
        except ValueError:
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), 120_000)
        return hmac.compare_digest(digest.hex(), digest_hex)
