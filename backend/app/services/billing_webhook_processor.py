r"""
Idempotent webhook handling: credits for one-time packs, subscription rows for recurring plans.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.observability import get_logger
from app.models.billing_checkout_session import BillingCheckoutSessionModel
from app.models.billing_dispute import BillingDisputeModel
from app.models.billing_invoice import BillingInvoiceModel
from app.models.billing_product import BillingProductModel
from app.models.billing_refund import BillingRefundModel
from app.models.payment_webhook_event import PaymentWebhookEventModel
from app.models.user import UserModel
from app.models.user_subscription import UserSubscriptionModel
from app.portability.payments.protocols import PaymentWebhookProcessorPort
from app.portability.payments.types import PaymentProvider, PaymentWebhookEvent
from app.services.billing_constants import BillingProductKind
from app.services.gst_invoice_service import issue_invoice_for_payment

logger = get_logger(__name__)


class BillingPaymentWebhookProcessor(PaymentWebhookProcessorPort):
    """Persists webhook idempotency then applies entitlements (extensible for new kinds)."""

    def __init__(self, *, db: Session) -> None:
        self._db = db

    def process(self, event: PaymentWebhookEvent) -> None:
        row = PaymentWebhookEventModel(
            id=str(uuid4()),
            provider=event.provider.value,
            provider_event_id=event.provider_event_id,
        )
        self._db.add(row)
        try:
            self._db.flush()
        except IntegrityError:
            self._db.rollback()
            return

        try:
            if event.provider is PaymentProvider.STRIPE:
                if event.event_type.startswith("refund.") or event.event_type.startswith("charge.dispute."):
                    self._stripe_compliance(event)
                else:
                    self._process_stripe(event)
            elif event.provider is PaymentProvider.RAZORPAY:
                if event.event_type.startswith("refund."):
                    self._razorpay_refund(event)
                else:
                    self._process_razorpay(event)
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise

    def _stripe_compliance(self, event: PaymentWebhookEvent) -> None:
        if event.event_type.startswith("refund."):
            self._upsert_refund_row(
                provider=PaymentProvider.STRIPE.value,
                provider_refund_id=event.refund_id,
                provider_payment_id=event.provider_payment_id,
                amount_minor=event.amount_minor,
                currency=event.currency,
                status=event.refund_status or "unknown",
                user_hint=event.metadata.get("user_id") or event.client_reference_id,
                raw=event.raw_payload,
            )
            self._touch_invoice_refund(PaymentProvider.STRIPE.value, event.provider_payment_id, event.amount_minor)
        elif event.event_type.startswith("charge.dispute."):
            self._upsert_dispute_row(
                provider=PaymentProvider.STRIPE.value,
                provider_dispute_id=event.dispute_id,
                provider_payment_id=event.provider_payment_id,
                amount_minor=event.amount_minor,
                currency=event.currency,
                status=event.dispute_status or "open",
                raw=event.raw_payload,
            )

    def _razorpay_refund(self, event: PaymentWebhookEvent) -> None:
        self._upsert_refund_row(
            provider=PaymentProvider.RAZORPAY.value,
            provider_refund_id=event.refund_id,
            provider_payment_id=event.provider_payment_id,
            amount_minor=event.amount_minor,
            currency=event.currency,
            status=event.refund_status or event.event_type,
            user_hint=event.metadata.get("user_id") or event.client_reference_id,
            raw=event.raw_payload,
        )
        self._touch_invoice_refund(PaymentProvider.RAZORPAY.value, event.provider_payment_id, event.amount_minor)

    def _upsert_refund_row(
        self,
        *,
        provider: str,
        provider_refund_id: str | None,
        provider_payment_id: str | None,
        amount_minor: int | None,
        currency: str | None,
        status: str,
        user_hint: str | None,
        raw: dict,
    ) -> None:
        if not provider_refund_id:
            return
        existing = (
            self._db.query(BillingRefundModel)
            .filter(BillingRefundModel.provider == provider, BillingRefundModel.provider_refund_id == provider_refund_id)
            .one_or_none()
        )
        uid = user_hint or self._user_id_from_invoice(provider, provider_payment_id)
        now = datetime.now(timezone.utc)
        payload = json.dumps(raw)[:16000]
        if existing is not None:
            existing.status = status
            if amount_minor is not None:
                existing.amount_minor = int(amount_minor)
            if currency:
                existing.currency = currency.upper()
            existing.updated_at = now
            existing.raw_json = payload
            if uid and existing.user_id is None:
                existing.user_id = uid
            return
        self._db.add(
            BillingRefundModel(
                id=str(uuid4()),
                user_id=uid,
                provider=provider,
                provider_refund_id=provider_refund_id,
                provider_payment_id=provider_payment_id,
                amount_minor=int(amount_minor or 0),
                currency=(currency or "INR").upper(),
                status=status,
                reason=None,
                initiated_by="webhook",
                raw_json=payload,
                created_at=now,
                updated_at=now,
            )
        )

    def _upsert_dispute_row(
        self,
        *,
        provider: str,
        provider_dispute_id: str | None,
        provider_payment_id: str | None,
        amount_minor: int | None,
        currency: str | None,
        status: str,
        raw: dict,
    ) -> None:
        if not provider_dispute_id:
            return
        existing = (
            self._db.query(BillingDisputeModel)
            .filter(
                BillingDisputeModel.provider == provider,
                BillingDisputeModel.provider_dispute_id == provider_dispute_id,
            )
            .one_or_none()
        )
        uid = self._user_id_from_invoice(provider, provider_payment_id)
        now = datetime.now(timezone.utc)
        payload = json.dumps(raw)[:16000]
        reason = None
        obj = raw.get("data", {}).get("object", {})
        if isinstance(obj, dict):
            reason = str(obj.get("reason") or "") or None
        opened_at: datetime | None = None
        if isinstance(obj, dict):
            oc = obj.get("created")
            if isinstance(oc, (int, float)):
                opened_at = datetime.fromtimestamp(int(oc), tz=timezone.utc)

        if existing is not None:
            existing.status = status
            existing.amount_minor = int(amount_minor) if amount_minor is not None else existing.amount_minor
            if currency:
                existing.currency = currency.upper()
            existing.reason_code = reason or existing.reason_code
            existing.updated_at = now
            existing.raw_json = payload
            if status in {"won", "lost", "charge_refunded", "warning_closed"}:
                existing.closed_at = existing.closed_at or now
            return

        initial_closed = now if status in {"won", "lost", "charge_refunded", "warning_closed"} else None
        self._db.add(
            BillingDisputeModel(
                id=str(uuid4()),
                user_id=uid,
                provider=provider,
                provider_dispute_id=provider_dispute_id,
                provider_payment_id=provider_payment_id,
                amount_minor=int(amount_minor) if amount_minor is not None else None,
                currency=(currency or "").upper() if currency else None,
                status=status,
                reason_code=reason,
                opened_at=opened_at or now,
                closed_at=initial_closed,
                raw_json=payload,
                created_at=now,
                updated_at=now,
            )
        )

    def _user_id_from_invoice(self, provider: str, provider_payment_id: str | None) -> str | None:
        if not provider_payment_id:
            return None
        inv = (
            self._db.query(BillingInvoiceModel)
            .filter(
                BillingInvoiceModel.provider == provider,
                BillingInvoiceModel.provider_payment_id == provider_payment_id,
            )
            .one_or_none()
        )
        return inv.user_id if inv is not None else None

    def _touch_invoice_refund(self, provider: str, provider_payment_id: str | None, refund_amount_minor: int | None) -> None:
        if not provider_payment_id:
            return
        inv = (
            self._db.query(BillingInvoiceModel)
            .filter(
                BillingInvoiceModel.provider == provider,
                BillingInvoiceModel.provider_payment_id == provider_payment_id,
            )
            .one_or_none()
        )
        if inv is None:
            return
        if refund_amount_minor is not None and int(refund_amount_minor) >= int(inv.amount_minor):
            inv.status = "refunded"
        else:
            inv.status = "partially_refunded"

    def _process_stripe(self, event: PaymentWebhookEvent) -> None:
        if event.event_type == "checkout.session.completed" and event.paid:
            self._stripe_checkout_completed(event)
        elif event.event_type == "customer.subscription.updated":
            self._stripe_subscription_updated(event)

    def _process_razorpay(self, event: PaymentWebhookEvent) -> None:
        if event.event_type.startswith("subscription."):
            self._razorpay_subscription_event(event)
            return
        if event.paid and event.event_type in {"payment.captured", "order.paid"}:
            self._apply_credit_pack_from_metadata(event)

    def _stripe_checkout_completed(self, event: PaymentWebhookEvent) -> None:
        if event.checkout_session_id:
            bcs = (
                self._db.query(BillingCheckoutSessionModel)
                .filter(BillingCheckoutSessionModel.provider_checkout_id == event.checkout_session_id)
                .one_or_none()
            )
            if bcs is not None:
                bcs.status = "completed"

        sku = event.metadata.get("product_sku")
        user_id = event.metadata.get("user_id") or event.client_reference_id
        if not sku or not user_id:
            return

        product = self._db.query(BillingProductModel).filter(BillingProductModel.sku == sku).one_or_none()
        if product is None:
            logger.warning("billing_webhook_unknown_product_sku", extra={"sku": sku})
            return

        if product.kind == BillingProductKind.ONE_TIME_CREDIT_PACK:
            self._apply_credits_to_user(user_id, product)
        elif product.kind == BillingProductKind.SUBSCRIPTION and event.subscription_id:
            self._upsert_subscription(
                user_id=user_id,
                product=product,
                external_subscription_id=event.subscription_id,
                status="active",
                current_period_end=None,
                provider=PaymentProvider.STRIPE.value,
            )
        self._maybe_issue_invoice(
            user_id=user_id,
            product=product,
            provider=PaymentProvider.STRIPE.value,
            provider_payment_id=event.provider_payment_id,
            provider_order_id=None,
            checkout_session_id=event.checkout_session_id,
            amount_minor=int(event.amount_minor or 0),
            currency=event.currency or "USD",
        )

    def _stripe_subscription_updated(self, event: PaymentWebhookEvent) -> None:
        if not event.subscription_id:
            return
        existing = (
            self._db.query(UserSubscriptionModel)
            .filter(
                UserSubscriptionModel.provider == PaymentProvider.STRIPE.value,
                UserSubscriptionModel.external_subscription_id == event.subscription_id,
            )
            .one_or_none()
        )
        now = datetime.now(timezone.utc)
        status = (event.subscription_status or "unknown").lower()
        user_id = event.metadata.get("user_id") or (existing.user_id if existing else None)
        product: BillingProductModel | None = None
        sku = event.metadata.get("product_sku")
        if sku:
            product = self._db.query(BillingProductModel).filter(BillingProductModel.sku == sku).one_or_none()

        current_period_end: datetime | None = None
        obj = event.raw_payload.get("data", {}).get("object", {})
        if isinstance(obj, dict):
            ts = obj.get("current_period_end")
            if isinstance(ts, (int, float)):
                current_period_end = datetime.fromtimestamp(int(ts), tz=timezone.utc)

        if existing is not None:
            existing.status = status
            existing.cancel_at_period_end = status in {"canceled", "unpaid"}
            existing.updated_at = now
            existing.current_period_end = current_period_end or existing.current_period_end
            if product is not None:
                existing.product_id = product.id
            return

        if not user_id:
            return

        self._upsert_subscription(
            user_id=user_id,
            product=product,
            external_subscription_id=event.subscription_id,
            status=status,
            current_period_end=current_period_end,
            provider=PaymentProvider.STRIPE.value,
        )

    def _razorpay_subscription_event(self, event: PaymentWebhookEvent) -> None:
        if not event.subscription_id:
            return
        user_id = event.metadata.get("user_id")
        sku = event.metadata.get("product_sku")
        if not user_id or not sku:
            return
        product = self._db.query(BillingProductModel).filter(BillingProductModel.sku == sku).one_or_none()
        status = (event.subscription_status or "active").lower()
        self._upsert_subscription(
            user_id=user_id,
            product=product,
            external_subscription_id=event.subscription_id,
            status=status,
            current_period_end=None,
            provider=PaymentProvider.RAZORPAY.value,
        )

    def _apply_credit_pack_from_metadata(self, event: PaymentWebhookEvent) -> None:
        sku = event.metadata.get("product_sku")
        user_id = event.metadata.get("user_id") or event.client_reference_id
        if not sku or not user_id:
            return
        product = self._db.query(BillingProductModel).filter(BillingProductModel.sku == sku).one_or_none()
        if product is None or product.kind != BillingProductKind.ONE_TIME_CREDIT_PACK:
            return
        self._apply_credits_to_user(user_id, product)
        self._maybe_issue_invoice(
            user_id=user_id,
            product=product,
            provider=PaymentProvider.RAZORPAY.value,
            provider_payment_id=event.provider_payment_id,
            provider_order_id=event.provider_order_id,
            checkout_session_id=None,
            order_id_for_lookup=event.provider_order_id,
            amount_minor=int(event.amount_minor or 0),
            currency=event.currency or "INR",
        )

    def _maybe_issue_invoice(
        self,
        *,
        user_id: str,
        product: BillingProductModel,
        provider: str,
        provider_payment_id: str | None,
        provider_order_id: str | None,
        checkout_session_id: str | None,
        amount_minor: int,
        currency: str,
        order_id_for_lookup: str | None = None,
    ) -> None:
        settings = get_settings()
        user = self._db.get(UserModel, user_id)
        if user is None:
            return
        bcs: BillingCheckoutSessionModel | None = None
        if provider == PaymentProvider.STRIPE.value and checkout_session_id:
            bcs = (
                self._db.query(BillingCheckoutSessionModel)
                .filter(
                    BillingCheckoutSessionModel.provider == PaymentProvider.STRIPE.value,
                    BillingCheckoutSessionModel.provider_checkout_id == checkout_session_id,
                )
                .one_or_none()
            )
        elif provider == PaymentProvider.RAZORPAY.value and order_id_for_lookup:
            bcs = (
                self._db.query(BillingCheckoutSessionModel)
                .filter(
                    BillingCheckoutSessionModel.provider == PaymentProvider.RAZORPAY.value,
                    BillingCheckoutSessionModel.provider_checkout_id == order_id_for_lookup,
                )
                .one_or_none()
            )
        issue_invoice_for_payment(
            self._db,
            settings=settings,
            user=user,
            product=product,
            provider=provider,
            provider_payment_id=provider_payment_id,
            provider_order_id=provider_order_id,
            checkout_session=bcs,
            amount_minor=amount_minor,
            currency=currency,
        )

    def _apply_credits_to_user(self, user_id: str, product: BillingProductModel) -> None:
        user = self._db.get(UserModel, user_id)
        if user is None:
            logger.warning("billing_webhook_unknown_user", extra={"user_id": user_id})
            return
        user.quota_lifetime_bonus = int(user.quota_lifetime_bonus) + int(product.credits_lifetime_bonus)
        user.quota_daily_bonus = int(user.quota_daily_bonus) + int(product.credits_daily_bonus)

    def _upsert_subscription(
        self,
        *,
        user_id: str,
        product: BillingProductModel | None,
        external_subscription_id: str,
        status: str,
        current_period_end: datetime | None,
        provider: str,
    ) -> None:
        row = (
            self._db.query(UserSubscriptionModel)
            .filter(
                UserSubscriptionModel.provider == provider,
                UserSubscriptionModel.external_subscription_id == external_subscription_id,
            )
            .one_or_none()
        )
        now = datetime.now(timezone.utc)
        if row is None:
            self._db.add(
                UserSubscriptionModel(
                    id=str(uuid4()),
                    user_id=user_id,
                    product_id=product.id if product else None,
                    provider=provider,
                    external_subscription_id=external_subscription_id,
                    status=status,
                    current_period_end=current_period_end,
                    cancel_at_period_end=status in {"canceled", "unpaid", "cancelled"},
                    created_at=now,
                    updated_at=now,
                )
            )
            return
        row.status = status
        if current_period_end is not None:
            row.current_period_end = current_period_end
        row.updated_at = now
        row.cancel_at_period_end = status in {"canceled", "unpaid", "cancelled"}
        if product is not None:
            row.product_id = product.id
