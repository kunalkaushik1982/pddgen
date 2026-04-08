r"""
Purpose: SQLAlchemy model for an application user that can own draft sessions.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\models\user.py
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user_auth_token import UserAuthTokenModel
    from app.models.user_password_reset_token import UserPasswordResetTokenModel


class UserModel(Base):
    """Persist one application user."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    auth_tokens: Mapped[list["UserAuthTokenModel"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    password_reset_tokens: Mapped[list["UserPasswordResetTokenModel"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
