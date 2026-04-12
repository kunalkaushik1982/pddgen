r"""
Tracks checkout attempts linked to catalog products (and provider session ids).
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class BillingCheckoutSessionModel(Base):
    """Binds a user + optional catalog product to a provider checkout id."""

    __tablename__ = "billing_checkout_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    product_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("billing_products.id", ondelete="SET NULL"), nullable=True, index=True
    )
    provider: Mapped[str] = mapped_column(String(16), nullable=False)
    provider_checkout_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    user: Mapped["UserModel"] = relationship()  # noqa: F821
    product: Mapped["BillingProductModel | None"] = relationship(  # noqa: F821
        "BillingProductModel",
        back_populates="checkout_sessions",
    )
