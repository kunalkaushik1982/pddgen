r"""
Map ``BillingProductModel`` rows to public API DTOs (provider hints).
"""

from __future__ import annotations

from typing import Literal

from app.models.billing_product import BillingProductModel
from app.schemas.billing import BillingProductPublic
from app.services.billing.billing_constants import BillingProductKind


def available_providers_for_product(product: BillingProductModel) -> list[Literal["stripe", "razorpay"]]:
    out: list[Literal["stripe", "razorpay"]] = []
    if product.kind == BillingProductKind.ONE_TIME_CREDIT_PACK:
        out.extend(["stripe", "razorpay"])
    elif product.kind == BillingProductKind.SUBSCRIPTION:
        if (product.stripe_price_id or "").strip():
            out.append("stripe")
        if (product.razorpay_plan_id or "").strip():
            out.append("razorpay")
    else:
        out.extend(["stripe", "razorpay"])
    return out


def to_public(product: BillingProductModel) -> BillingProductPublic:
    return BillingProductPublic(
        id=product.id,
        sku=product.sku,
        kind=product.kind,
        title=product.title,
        credits_lifetime_bonus=int(product.credits_lifetime_bonus),
        credits_daily_bonus=int(product.credits_daily_bonus),
        amount_minor=int(product.amount_minor),
        currency=product.currency,
        stripe_checkout_mode=product.stripe_checkout_mode,
        available_providers=available_providers_for_product(product),
    )
