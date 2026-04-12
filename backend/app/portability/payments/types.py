r"""
Provider-agnostic DTOs for checkout and webhooks (stable core types).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PaymentProvider(str, Enum):
    STRIPE = "stripe"
    RAZORPAY = "razorpay"


@dataclass(frozen=True, slots=True)
class CheckoutSessionRequest:
    """Input for creating a payable checkout session (one-time payment)."""

    amount_minor: int
    currency: str
    success_url: str
    cancel_url: str
    client_reference_id: str
    title: str = "Payment"
    metadata: dict[str, str] = field(default_factory=dict)


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
