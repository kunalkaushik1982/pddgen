r"""
Active subscription rows (Stripe/Razorpay) tied to a catalog product where applicable.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserSubscriptionModel(Base):
    """External subscription id per provider (unique)."""

    __tablename__ = "user_subscriptions"
    __table_args__ = (UniqueConstraint("provider", "external_subscription_id", name="uq_user_sub_provider_ext_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    product_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("billing_products.id", ondelete="SET NULL"), nullable=True, index=True
    )
    provider: Mapped[str] = mapped_column(String(16), nullable=False)
    external_subscription_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="active", nullable=False)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    user: Mapped["UserModel"] = relationship()  # noqa: F821
    product: Mapped["BillingProductModel | None"] = relationship(  # noqa: F821
        "BillingProductModel",
        back_populates="subscriptions",
    )
