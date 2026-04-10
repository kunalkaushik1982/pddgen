r"""
Purpose: SQLAlchemy model for an application user that can own draft sessions.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\models\user.py
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user_auth_token import UserAuthTokenModel
    from app.models.user_email_verification_token import UserEmailVerificationTokenModel
    from app.models.user_password_reset_token import UserPasswordResetTokenModel


class UserModel(Base):
    """Persist one application user."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    admin_console_only: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    admin_preferences_json: Mapped[str] = mapped_column(Text(), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    auth_tokens: Mapped[list["UserAuthTokenModel"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    password_reset_tokens: Mapped[list["UserPasswordResetTokenModel"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    email_verification_tokens: Mapped[list["UserEmailVerificationTokenModel"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
