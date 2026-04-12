r"""
Razorpay adapter: Orders API + webhook verification (razorpay SDK).
"""

from __future__ import annotations

import json
from typing import Any, Mapping

import razorpay

from app.core.config import Settings
from app.portability.payments.exceptions import PaymentConfigurationError, PaymentGatewayRejectedError, PaymentWebhookVerificationError
from app.portability.payments.types import CheckoutSessionRequest, CheckoutSessionResult, PaymentProvider, PaymentWebhookEvent


def _header_ci(headers: Mapping[str, str], name: str) -> str | None:
    lower = {k.lower(): v for k, v in headers.items()}
    return lower.get(name.lower())


class RazorpayPaymentGateway:
    """Razorpay implementation of ``PaymentGatewayPort``."""

    def __init__(self, *, settings: Settings) -> None:
        self._settings = settings
        key_id = settings.payment_razorpay_key_id.strip()
        key_secret = settings.payment_razorpay_key_secret.strip()
        if not key_id or not key_secret:
            raise PaymentConfigurationError(
                "Razorpay key id/secret are not configured.",
                provider=PaymentProvider.RAZORPAY.value,
            )
        self._client = razorpay.Client(auth=(key_id, key_secret))
        self._key_id = key_id

    @property
    def provider(self) -> PaymentProvider:
        return PaymentProvider.RAZORPAY

    def create_checkout_session(self, request: CheckoutSessionRequest) -> CheckoutSessionResult:
        if request.amount_minor <= 0:
            raise PaymentGatewayRejectedError("amount_minor must be positive.", provider=self.provider.value)
        currency = request.currency.strip().upper()
        if len(currency) != 3:
            raise PaymentGatewayRejectedError("currency must be a 3-letter ISO code.", provider=self.provider.value)
        receipt = request.client_reference_id.replace("-", "")[:40] or "rcpt"
        notes = {k: str(v) for k, v in request.metadata.items()}
        notes.setdefault("client_reference_id", request.client_reference_id)
        try:
            order = self._client.order.create(
                {
                    "amount": request.amount_minor,
                    "currency": currency,
                    "receipt": receipt,
                    "notes": notes,
                }
            )
        except razorpay.errors.BadRequestError as exc:  # type: ignore[attr-defined]
            raise PaymentGatewayRejectedError(str(exc), provider=self.provider.value) from exc

        oid = order.get("id") if isinstance(order, dict) else None
        if not isinstance(oid, str):
            raise PaymentGatewayRejectedError("Razorpay order id missing.", provider=self.provider.value)
        client_payload: dict[str, Any] = {
            "key_id": self._key_id,
            "order_id": oid,
            "amount": order.get("amount"),
            "currency": order.get("currency"),
            "client_reference_id": request.client_reference_id,
        }
        return CheckoutSessionResult(
            provider=self.provider,
            provider_session_id=oid,
            redirect_url=None,
            client_payload=client_payload,
        )

    def verify_and_parse_webhook(self, *, raw_body: bytes, headers: Mapping[str, str]) -> PaymentWebhookEvent:
        secret = self._settings.payment_razorpay_webhook_secret.strip()
        if not secret:
            raise PaymentConfigurationError("Razorpay webhook secret is not configured.", provider=self.provider.value)
        signature = _header_ci(headers, "X-Razorpay-Signature")
        if not signature:
            raise PaymentWebhookVerificationError("Missing X-Razorpay-Signature header.", provider=self.provider.value)
        body_text = raw_body.decode("utf-8")
        try:
            self._client.utility.verify_webhook_signature(body_text, signature, secret)
        except razorpay.errors.SignatureVerificationError as exc:  # type: ignore[attr-defined]
            raise PaymentWebhookVerificationError("Razorpay signature verification failed.", provider=self.provider.value) from exc

        try:
            data = json.loads(body_text)
        except json.JSONDecodeError as exc:
            raise PaymentWebhookVerificationError("Invalid Razorpay webhook JSON.", provider=self.provider.value) from exc

        event_name = str(data.get("event", "") or "unknown")
        event_id = str(data.get("id") or data.get("created_at") or "razorpay-event")
        payload = data.get("payload") or {}
        paid = event_name in {"payment.captured", "order.paid"}
        amount_minor: int | None = None
        currency: str | None = None
        client_reference_id: str | None = None

        payment_entity = _dig(payload, "payment", "entity")
        if isinstance(payment_entity, dict):
            amt = payment_entity.get("amount")
            if amt is not None:
                amount_minor = int(amt)
            cur = payment_entity.get("currency")
            currency = str(cur).upper() if cur else None
            notes = payment_entity.get("notes") or {}
            if isinstance(notes, dict):
                cr = notes.get("client_reference_id")
                if cr:
                    client_reference_id = str(cr)

        order_entity = _dig(payload, "order", "entity")
        if client_reference_id is None and isinstance(order_entity, dict):
            notes = order_entity.get("notes") or {}
            if isinstance(notes, dict) and notes.get("client_reference_id"):
                client_reference_id = str(notes.get("client_reference_id"))

        return PaymentWebhookEvent(
            provider=self.provider,
            event_type=event_name,
            provider_event_id=event_id,
            paid=paid,
            amount_minor=amount_minor,
            currency=currency,
            client_reference_id=client_reference_id,
            raw_payload=data if isinstance(data, dict) else {"payload": data},
        )


def _dig(obj: Any, *keys: str) -> Any:
    cur: Any = obj
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur
