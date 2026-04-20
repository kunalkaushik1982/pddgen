r"""
Admin-initiated refunds via Stripe / Razorpay APIs (server-side secrets).
"""

from __future__ import annotations

from typing import Any

import razorpay
import stripe

from app.core.config import Settings
from app.portability.payments.types import PaymentProvider


class BillingRefundInitiationError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def initiate_provider_refund(
    settings: Settings,
    *,
    provider: str,
    provider_payment_id: str,
    amount_minor: int | None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Create a refund; full amount when ``amount_minor`` is None (provider-specific)."""
    p = provider.strip().lower()
    if p == PaymentProvider.STRIPE.value:
        return _stripe_refund(settings, provider_payment_id=provider_payment_id, amount_minor=amount_minor)
    if p == PaymentProvider.RAZORPAY.value:
        return _razorpay_refund(settings, provider_payment_id=provider_payment_id, amount_minor=amount_minor, notes=notes)
    raise BillingRefundInitiationError(f"Unsupported provider: {provider}")


def _stripe_refund(settings: Settings, *, provider_payment_id: str, amount_minor: int | None) -> dict[str, Any]:
    secret = settings.payment_stripe_secret_key.strip()
    if not secret:
        raise BillingRefundInitiationError("Stripe is not configured.")
    stripe.api_key = secret
    try:
        params: dict[str, Any] = {"payment_intent": provider_payment_id}
        if amount_minor is not None:
            params["amount"] = int(amount_minor)
        ref = stripe.Refund.create(**params)
    except stripe.error.StripeError as exc:  # type: ignore[attr-defined]
        raise BillingRefundInitiationError(str(exc)) from exc
    return ref if isinstance(ref, dict) else ref.to_dict()  # type: ignore[union-attr]


def _razorpay_refund(
    settings: Settings,
    *,
    provider_payment_id: str,
    amount_minor: int | None,
    notes: str | None,
) -> dict[str, Any]:
    key_id = settings.payment_razorpay_key_id.strip()
    key_secret = settings.payment_razorpay_key_secret.strip()
    if not key_id or not key_secret:
        raise BillingRefundInitiationError("Razorpay is not configured.")
    client = razorpay.Client(auth=(key_id, key_secret))
    payload: dict[str, Any] = {}
    if amount_minor is not None:
        payload["amount"] = int(amount_minor)
    if notes:
        payload["notes"] = {"reason": notes[:200]}
    try:
        # Razorpay SDK exposes ``client.payment`` at runtime; package stubs omit it.
        result = client.payment.refund(provider_payment_id, payload)  # type: ignore[attr-defined]
    except razorpay.errors.BadRequestError as exc:  # type: ignore[attr-defined]
        raise BillingRefundInitiationError(str(exc)) from exc
    return result if isinstance(result, dict) else dict(result)
