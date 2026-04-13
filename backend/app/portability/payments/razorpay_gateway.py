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
        if request.checkout_mode == "subscription":
            return self._create_subscription(request)
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

    def _create_subscription(self, request: CheckoutSessionRequest) -> CheckoutSessionResult:
        plan_id = (request.razorpay_plan_id or "").strip()
        if not plan_id:
            raise PaymentGatewayRejectedError(
                "razorpay_plan_id is required for Razorpay subscription checkout.",
                provider=self.provider.value,
            )
        notes = {k: str(v) for k, v in request.metadata.items()}
        notes.setdefault("client_reference_id", request.client_reference_id)
        try:
            sub = self._client.subscription.create(
                {
                    "plan_id": plan_id,
                    "customer_notify": 1,
                    "total_count": 60,
                    "quantity": 1,
                    "notes": notes,
                }
            )
        except razorpay.errors.BadRequestError as exc:  # type: ignore[attr-defined]
            raise PaymentGatewayRejectedError(str(exc), provider=self.provider.value) from exc

        sid = sub.get("id") if isinstance(sub, dict) else None
        if not isinstance(sid, str):
            raise PaymentGatewayRejectedError("Razorpay subscription id missing.", provider=self.provider.value)
        short_url = sub.get("short_url") if isinstance(sub, dict) else None
        client_payload: dict[str, Any] = {
            "key_id": self._key_id,
            "subscription_id": sid,
            "status": sub.get("status"),
            "razorpay_plan_id": plan_id,
            "client_reference_id": request.client_reference_id,
        }
        return CheckoutSessionResult(
            provider=self.provider,
            provider_session_id=sid,
            redirect_url=short_url if isinstance(short_url, str) else None,
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
        payload = data.get("payload") or {}
        amount_minor: int | None = None
        currency: str | None = None
        client_reference_id: str | None = None
        provider_payment_id: str | None = None
        provider_order_id: str | None = None
        refund_id: str | None = None
        dispute_id: str | None = None
        refund_status: str | None = None
        dispute_status: str | None = None
        meta: dict[str, str] = {}
        subscription_id: str | None = None
        subscription_status: str | None = None

        paid = event_name in {"payment.captured", "order.paid", "subscription.charged", "invoice.paid"}

        payment_entity = _dig(payload, "payment", "entity")
        if isinstance(payment_entity, dict):
            pid = payment_entity.get("id")
            if pid:
                provider_payment_id = str(pid)
            oid = payment_entity.get("order_id")
            if oid:
                provider_order_id = str(oid)
            amt = payment_entity.get("amount")
            if amt is not None:
                amount_minor = int(amt)
            cur = payment_entity.get("currency")
            currency = str(cur).upper() if cur else None
            notes = payment_entity.get("notes") or {}
            if isinstance(notes, dict):
                meta.update({str(k): str(v) for k, v in notes.items()})
                cr = notes.get("client_reference_id")
                if cr:
                    client_reference_id = str(cr)

        order_entity = _dig(payload, "order", "entity")
        if isinstance(order_entity, dict):
            oid = order_entity.get("id")
            if oid and not provider_order_id:
                provider_order_id = str(oid)
            notes = order_entity.get("notes") or {}
            if isinstance(notes, dict):
                meta.update({str(k): str(v) for k, v in notes.items()})
                if client_reference_id is None and notes.get("client_reference_id"):
                    client_reference_id = str(notes.get("client_reference_id"))

        refund_entity = _dig(payload, "refund", "entity")
        if isinstance(refund_entity, dict):
            rid = refund_entity.get("id")
            if rid:
                refund_id = str(rid)
            refund_status = str(refund_entity.get("status") or "") or None
            pay_id = refund_entity.get("payment_id")
            if pay_id:
                provider_payment_id = str(pay_id)
            amt = refund_entity.get("amount")
            if amt is not None:
                amount_minor = int(amt)
            if not currency:
                cur = refund_entity.get("currency")
                currency = str(cur).upper() if cur else None
            notes = refund_entity.get("notes") or {}
            if isinstance(notes, dict):
                meta.update({str(k): str(v) for k, v in notes.items()})

        sub_entity = _dig(payload, "subscription", "entity")
        if isinstance(sub_entity, dict):
            sid = sub_entity.get("id")
            if sid:
                subscription_id = str(sid)
            subscription_status = str(sub_entity.get("status") or "") or None
            sub_notes = sub_entity.get("notes") or {}
            if isinstance(sub_notes, dict):
                meta.update({str(k): str(v) for k, v in sub_notes.items()})
            if not client_reference_id and meta.get("client_reference_id"):
                client_reference_id = str(meta.get("client_reference_id"))
            if event_name.startswith("subscription.") and event_name not in {"subscription.charged"}:
                paid = subscription_status in {"active", "authenticated", "charged"}

        # Idempotency key: must be unique per webhook delivery. Razorpay sends X-Razorpay-Event-Id per request.
        # Never fall back to created_at alone — multiple events in the same second would collide and skip processing.
        header_event_id = (_header_ci(headers, "X-Razorpay-Event-Id") or "").strip()
        body_id = data.get("id")
        body_id_str = str(body_id).strip() if body_id not in (None, "") else ""
        if header_event_id:
            event_id = header_event_id
        elif body_id_str:
            event_id = body_id_str
        else:
            ts = data.get("created_at")
            ref = provider_payment_id or provider_order_id or subscription_id or refund_id or "unknown"
            event_id = f"razorpay:{event_name}:{ts}:{ref}"

        return PaymentWebhookEvent(
            provider=self.provider,
            event_type=event_name,
            provider_event_id=event_id,
            paid=paid,
            amount_minor=amount_minor,
            currency=currency,
            client_reference_id=client_reference_id,
            raw_payload=data if isinstance(data, dict) else {"payload": data},
            metadata=meta,
            checkout_session_id=None,
            subscription_id=subscription_id,
            subscription_status=subscription_status,
            provider_payment_id=provider_payment_id,
            provider_order_id=provider_order_id,
            refund_id=refund_id,
            dispute_id=dispute_id,
            refund_status=refund_status,
            dispute_status=dispute_status,
        )


def _dig(obj: Any, *keys: str) -> Any:
    cur: Any = obj
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur
