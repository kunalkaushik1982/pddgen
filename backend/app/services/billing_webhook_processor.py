r"""
Idempotent webhook handling: credits for one-time packs, subscription rows for recurring plans.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.observability import get_logger
from app.models.billing_checkout_session import BillingCheckoutSessionModel
from app.models.billing_product import BillingProductModel
from app.models.payment_webhook_event import PaymentWebhookEventModel
from app.models.user import UserModel
from app.models.user_subscription import UserSubscriptionModel
from app.portability.payments.protocols import PaymentWebhookProcessorPort
from app.portability.payments.types import PaymentProvider, PaymentWebhookEvent
from app.services.billing_constants import BillingProductKind

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
                self._process_stripe(event)
            elif event.provider is PaymentProvider.RAZORPAY:
                self._process_razorpay(event)
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise

    def _process_stripe(self, event: PaymentWebhookEvent) -> None:
        if event.event_type == "checkout.session.completed" and event.paid:
            self._stripe_checkout_completed(event)
        elif event.event_type == "customer.subscription.updated":
            self._stripe_subscription_updated(event)

    def _process_razorpay(self, event: PaymentWebhookEvent) -> None:
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

        if existing is not None:
            existing.status = status
            existing.cancel_at_period_end = status in {"canceled", "unpaid"}
            existing.updated_at = now
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
            current_period_end=None,
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
    ) -> None:
        row = (
            self._db.query(UserSubscriptionModel)
            .filter(
                UserSubscriptionModel.provider == PaymentProvider.STRIPE.value,
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
                    provider=PaymentProvider.STRIPE.value,
                    external_subscription_id=external_subscription_id,
                    status=status,
                    current_period_end=current_period_end,
                    cancel_at_period_end=status in {"canceled", "unpaid"},
                    created_at=now,
                    updated_at=now,
                )
            )
            return
        row.status = status
        row.current_period_end = current_period_end
        row.updated_at = now
        if product is not None:
            row.product_id = product.id
