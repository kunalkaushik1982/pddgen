r"""
Purpose: Database-backed session token service.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\database_session_service.py
"""

from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.user import UserModel
from app.models.user_auth_token import UserAuthTokenModel


class DatabaseSessionService:
    """Persist backend auth sessions in the database."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def create_session(self, db: Session, *, user: UserModel) -> str:
        raw_token = secrets.token_urlsafe(32)
        db.add(
            UserAuthTokenModel(
                user_id=user.id,
                token_hash=self._hash_token(raw_token),
                expires_at=datetime.utcnow() + timedelta(days=self.settings.auth_token_days),
            )
        )
        return raw_token

    def revoke_session(self, db: Session, *, token: str) -> None:
        record = db.execute(
            select(UserAuthTokenModel).where(UserAuthTokenModel.token_hash == self._hash_token(token))
        ).scalar_one_or_none()
        if record is None:
            return
        db.delete(record)
        db.commit()

    def resolve_user(self, db: Session, *, token: str) -> UserModel:
        record = db.execute(
            select(UserAuthTokenModel).where(UserAuthTokenModel.token_hash == self._hash_token(token))
        ).scalar_one_or_none()
        if record is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

        current_time = (
            datetime.now(record.expires_at.tzinfo)
            if record.expires_at.tzinfo
            else datetime.now(timezone.utc).replace(tzinfo=None)
        )
        if record.expires_at < current_time:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
        return record.user

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
