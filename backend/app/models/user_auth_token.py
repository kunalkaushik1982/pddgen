r"""
Purpose: SQLAlchemy model for simple API auth tokens.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\models\user_auth_token.py
"""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import UserModel


class UserAuthTokenModel(Base):
    """Persist one active API auth token."""

    __tablename__ = "user_auth_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.utcnow() + timedelta(days=7),
        index=True,
    )

    user: Mapped["UserModel"] = relationship(back_populates="auth_tokens")
