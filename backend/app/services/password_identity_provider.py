r"""
Purpose: Built-in username/password identity provider.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\password_identity_provider.py
"""

import hashlib
import hmac
import secrets

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import UserModel


class PasswordIdentityProvider:
    """Authenticate users against the local username/password store."""

    provider_name = "password"

    def register(self, db: Session, *, username: str, password: str) -> UserModel:
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
        return user

    def authenticate(self, db: Session, *, username: str, password: str) -> UserModel:
        normalized_username = username.strip()
        user = db.execute(select(UserModel).where(UserModel.username == normalized_username)).scalar_one_or_none()
        if user is None or not self._verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password.")
        return user

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
