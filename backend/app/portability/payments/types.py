r"""
Provider-agnostic DTOs for checkout and webhooks (stable core types).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal


class PaymentProvider(str, Enum):
    STRIPE = "stripe"
    RAZORPAY = "razorpay"


CheckoutMode = Literal["payment", "subscription"]


@dataclass(frozen=True, slots=True)
class CheckoutSessionRequest:
    """Input for creating a Stripe Checkout session or Razorpay order."""

    amount_minor: int
    currency: str
    success_url: str
    cancel_url: str
    client_reference_id: str
    title: str = "Payment"
    metadata: dict[str, str] = field(default_factory=dict)
    checkout_mode: CheckoutMode = "payment"
    """``payment`` (one-time) or ``subscription`` (Stripe Checkout or Razorpay Subscriptions API)."""

    stripe_price_id: str | None = None
    """When ``checkout_mode`` is ``subscription``, Stripe Checkout line item uses this Price id."""

    stripe_subscription_data_metadata: dict[str, str] = field(default_factory=dict)
    """Merged into Stripe ``subscription_data.metadata`` for subscription checkouts."""

    razorpay_plan_id: str | None = None
    """When ``checkout_mode`` is ``subscription``, Razorpay ``plan_id`` for ``subscription.create``."""


@dataclass(frozen=True, slots=True)
class CheckoutSessionResult:
    """Provider-specific checkout hand-off (redirect URL and/or fields for client SDK)."""

    provider: PaymentProvider
    provider_session_id: str
    redirect_url: str | None
    client_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PaymentWebhookEvent:
    """Normalized webhook after signature verification (domain layer consumes this)."""

    provider: PaymentProvider
    event_type: str
    provider_event_id: str
    paid: bool
    amount_minor: int | None
    currency: str | None
    client_reference_id: str | None
    raw_payload: dict[str, Any]
    metadata: dict[str, str] = field(default_factory=dict)
    checkout_session_id: str | None = None
    subscription_id: str | None = None
    subscription_status: str | None = None
    provider_payment_id: str | None = None
    provider_order_id: str | None = None
    refund_id: str | None = None
    dispute_id: str | None = None
    refund_status: str | None = None
    dispute_status: str | None = None
