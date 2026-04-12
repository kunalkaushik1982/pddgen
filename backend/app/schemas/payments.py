r"""
API schemas for payment checkout (provider-agnostic envelope).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator


class PaymentCheckoutRequest(BaseModel):
    """Start checkout: either a catalog ``product_sku`` or a custom ``amount_minor`` + ``currency``."""

    provider: Literal["stripe", "razorpay"]
    product_sku: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
        description="When set, amount/currency come from billing_products (server-side).",
    )
    amount_minor: int | None = Field(
        default=None,
        gt=0,
        description="Custom one-time amount (smallest currency unit). Ignored when product_sku is set.",
    )
    currency: str | None = Field(
        default=None,
        min_length=3,
        max_length=3,
        description="ISO 4217 code. Required for custom checkout; ignored when product_sku is set.",
    )
    success_url: HttpUrl
    cancel_url: HttpUrl
    title: str = Field(default="Payment", min_length=1, max_length=200)
    metadata: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def product_or_custom_amount(self) -> PaymentCheckoutRequest:
        if self.product_sku is not None and self.product_sku.strip():
            if self.amount_minor is not None or self.currency is not None:
                raise ValueError("Do not pass amount_minor or currency when product_sku is set.")
            return self
        if self.amount_minor is None or not self.currency:
            raise ValueError("amount_minor and currency are required when product_sku is omitted.")
        return self


class PaymentCheckoutResponse(BaseModel):
    """Client uses redirect_url (Stripe) or client_payload (Razorpay JS) to complete payment."""

    provider: str
    provider_session_id: str
    redirect_url: str | None = None
    client_payload: dict[str, Any] = Field(default_factory=dict)
