r"""
Stripe adapter: Checkout Session + webhook verification (stripe SDK).
"""

from __future__ import annotations

from typing import Any, Mapping

import stripe

from app.core.config import Settings
from app.portability.payments.exceptions import PaymentConfigurationError, PaymentGatewayRejectedError, PaymentWebhookVerificationError
from app.portability.payments.types import CheckoutSessionRequest, CheckoutSessionResult, PaymentProvider, PaymentWebhookEvent


class StripePaymentGateway:
    """Stripe implementation of ``PaymentGatewayPort``."""

    def __init__(self, *, settings: Settings) -> None:
        self._settings = settings
        secret = settings.payment_stripe_secret_key.strip()
        if not secret:
            raise PaymentConfigurationError("Stripe secret key is not configured.", provider=PaymentProvider.STRIPE.value)
        stripe.api_key = secret

    @property
    def provider(self) -> PaymentProvider:
        return PaymentProvider.STRIPE

    def create_checkout_session(self, request: CheckoutSessionRequest) -> CheckoutSessionResult:
        if request.amount_minor <= 0:
            raise PaymentGatewayRejectedError("amount_minor must be positive.", provider=self.provider.value)
        currency = request.currency.strip().lower()
        if len(currency) != 3:
            raise PaymentGatewayRejectedError("currency must be a 3-letter ISO code.", provider=self.provider.value)
        try:
            session = stripe.checkout.Session.create(
                mode="payment",
                success_url=request.success_url,
                cancel_url=request.cancel_url,
                client_reference_id=request.client_reference_id,
                metadata=request.metadata,
                line_items=[
                    {
                        "price_data": {
                            "currency": currency,
                            "unit_amount": request.amount_minor,
                            "product_data": {"name": request.title},
                        },
                        "quantity": 1,
                    }
                ],
            )
        except stripe.error.StripeError as exc:  # type: ignore[attr-defined]
            raise PaymentGatewayRejectedError(str(exc), provider=self.provider.value) from exc

        url = session.url if isinstance(session.url, str) else None
        sid = session.get("id") if isinstance(session, dict) else getattr(session, "id", None)
        if not isinstance(sid, str):
            raise PaymentGatewayRejectedError("Stripe session id missing.", provider=self.provider.value)
        payload: dict[str, Any] = {}
        if self._settings.payment_stripe_publishable_key.strip():
            payload["publishable_key"] = self._settings.payment_stripe_publishable_key.strip()
        return CheckoutSessionResult(
            provider=self.provider,
            provider_session_id=sid,
            redirect_url=url,
            client_payload=payload,
        )

    def verify_and_parse_webhook(self, *, raw_body: bytes, headers: Mapping[str, str]) -> PaymentWebhookEvent:
        secret = self._settings.payment_stripe_webhook_secret.strip()
        if not secret:
            raise PaymentConfigurationError("Stripe webhook secret is not configured.", provider=self.provider.value)
        sig = headers.get("stripe-signature") or headers.get("Stripe-Signature")
        if not sig:
            raise PaymentWebhookVerificationError("Missing Stripe-Signature header.", provider=self.provider.value)
        try:
            event = stripe.Webhook.construct_event(raw_body, sig, secret)
        except ValueError as exc:
            raise PaymentWebhookVerificationError("Invalid Stripe webhook payload.", provider=self.provider.value) from exc
        except stripe.error.SignatureVerificationError as exc:  # type: ignore[attr-defined]
            raise PaymentWebhookVerificationError("Stripe signature verification failed.", provider=self.provider.value) from exc

        event_dict: dict[str, Any] = event if isinstance(event, dict) else event.to_dict()  # type: ignore[union-attr]

        event_id = str(event_dict.get("id", ""))
        event_type = str(event_dict.get("type", "unknown"))
        data_object = (event_dict.get("data") or {}).get("object") or {}
        paid = event_type in {"checkout.session.completed", "payment_intent.succeeded"}
        amount_minor: int | None = None
        currency: str | None = None
        client_reference_id: str | None = None
        if isinstance(data_object, dict):
            amount_minor = data_object.get("amount_total")
            if amount_minor is not None:
                amount_minor = int(amount_minor)
            cur = data_object.get("currency")
            currency = str(cur).upper() if cur else None
            cr = data_object.get("client_reference_id")
            client_reference_id = str(cr) if cr else None
        return PaymentWebhookEvent(
            provider=self.provider,
            event_type=event_type,
            provider_event_id=event_id,
            paid=paid,
            amount_minor=amount_minor,
            currency=currency,
            client_reference_id=client_reference_id,
            raw_payload=event_dict,
        )
