r"""
String constants for billing catalog ``kind`` and related enums (open for extension).
"""

from __future__ import annotations


class BillingProductKind:
    """Catalog product discriminator — add new kinds without breaking existing rows."""

    ONE_TIME_CREDIT_PACK = "one_time_credit_pack"
    SUBSCRIPTION = "subscription"
    CUSTOM = "custom"


class BillingCheckoutMode:
    """Stripe Checkout ``mode`` / stored on ``BillingProductModel.stripe_checkout_mode``."""

    PAYMENT = "payment"
    SUBSCRIPTION = "subscription"
