r"""
Billing catalog schemas (public list + admin CRUD).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class BillingProductPublic(BaseModel):
    """Safe fields for the checkout UI (no secrets)."""

    id: str
    sku: str
    kind: str
    title: str
    credits_lifetime_bonus: int
    credits_daily_bonus: int
    amount_minor: int
    currency: str
    stripe_checkout_mode: str
    available_providers: list[Literal["stripe", "razorpay"]]


class BillingProductAdminResponse(BaseModel):
    id: str
    sku: str
    kind: str
    title: str
    credits_lifetime_bonus: int
    credits_daily_bonus: int
    amount_minor: int
    currency: str
    stripe_price_id: str | None
    stripe_checkout_mode: str
    razorpay_plan_id: str | None
    active: bool
    extra_json: str


class BillingProductCreateRequest(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    kind: str = Field(min_length=1, max_length=32)
    title: str = Field(min_length=1, max_length=255)
    credits_lifetime_bonus: int = Field(default=0, ge=0)
    credits_daily_bonus: int = Field(default=0, ge=0)
    amount_minor: int = Field(default=0, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    stripe_price_id: str | None = None
    stripe_checkout_mode: str = Field(default="payment", max_length=16)
    razorpay_plan_id: str | None = None
    active: bool = True
    extra_json: str = "{}"


class BillingProductUpdateRequest(BaseModel):
    kind: str | None = Field(default=None, max_length=32)
    title: str | None = Field(default=None, max_length=255)
    credits_lifetime_bonus: int | None = Field(default=None, ge=0)
    credits_daily_bonus: int | None = Field(default=None, ge=0)
    amount_minor: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    stripe_price_id: str | None = None
    stripe_checkout_mode: str | None = Field(default=None, max_length=16)
    razorpay_plan_id: str | None = None
    active: bool | None = None
    extra_json: str | None = None
