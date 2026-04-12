r"""
Catalog rows for one-time credit packs, subscriptions, and future billing kinds.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class BillingProductModel(Base):
    """Sellable product: credit pack, subscription plan, or extensible kinds."""

    __tablename__ = "billing_products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    sku: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    kind: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        comment="one_time_credit_pack | subscription | custom",
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    credits_lifetime_bonus: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    credits_daily_bonus: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    stripe_price_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_checkout_mode: Mapped[str] = mapped_column(
        String(16), default="payment", nullable=False, comment="payment | subscription"
    )
    razorpay_plan_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    extra_json: Mapped[str] = mapped_column(Text(), default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    checkout_sessions: Mapped[list["BillingCheckoutSessionModel"]] = relationship(  # noqa: F821
        "BillingCheckoutSessionModel",
        back_populates="product",
    )
    subscriptions: Mapped[list["UserSubscriptionModel"]] = relationship(  # noqa: F821
        "UserSubscriptionModel",
        back_populates="product",
    )
