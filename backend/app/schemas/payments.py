r"""
API schemas for payment checkout (provider-agnostic envelope).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl


class PaymentCheckoutRequest(BaseModel):
    """Start a one-time checkout with either Stripe Checkout or a Razorpay order."""

    provider: Literal["stripe", "razorpay"]
    amount_minor: int = Field(gt=0, description="Amount in smallest currency unit (cents, paise, etc.).")
    currency: str = Field(min_length=3, max_length=3, description="ISO 4217 alphabetic code.")
    success_url: HttpUrl
    cancel_url: HttpUrl
    title: str = Field(default="Payment", min_length=1, max_length=200)
    metadata: dict[str, str] = Field(default_factory=dict)


class PaymentCheckoutResponse(BaseModel):
    """Client uses redirect_url (Stripe) or client_payload (Razorpay JS) to complete payment."""

    provider: str
    provider_session_id: str
    redirect_url: str | None = None
    client_payload: dict[str, Any] = Field(default_factory=dict)
