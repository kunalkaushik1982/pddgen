r"""
Catalog-aware checkout: resolves ``BillingProductModel`` and builds provider requests.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.billing_checkout_session import BillingCheckoutSessionModel
from app.models.billing_product import BillingProductModel
from app.models.user import UserModel
from app.portability.payments import (
    CheckoutSessionRequest,
    PaymentGatewayFactoryPort,
    PaymentProvider,
)
from app.portability.payments.types import CheckoutSessionResult
from app.schemas.payments import PaymentCheckoutRequest
from app.services.billing_constants import BillingCheckoutMode, BillingProductKind
from app.services.billing_exceptions import BillingProductNotFoundError, BillingRuleError


class BillingCheckoutService:
    """Orchestrates catalog + custom checkouts (DIP: uses ``PaymentGatewayFactoryPort``)."""

    def __init__(self, *, db: Session, factory: PaymentGatewayFactoryPort) -> None:
        self._db = db
        self._factory = factory

    def create_checkout(self, user: UserModel, body: PaymentCheckoutRequest) -> CheckoutSessionResult:
        if body.product_sku:
            return self._checkout_catalog_product(user, body)
        return self._checkout_custom_amount(user, body)

    def _checkout_catalog_product(self, user: UserModel, body: PaymentCheckoutRequest) -> CheckoutSessionResult:
        sku = (body.product_sku or "").strip()
        product = (
            self._db.query(BillingProductModel)
            .filter(BillingProductModel.sku == sku, BillingProductModel.active.is_(True))
            .one_or_none()
        )
        if product is None:
            raise BillingProductNotFoundError(sku)

        provider = PaymentProvider.STRIPE if body.provider == "stripe" else PaymentProvider.RAZORPAY

        if product.kind == BillingProductKind.SUBSCRIPTION and provider is PaymentProvider.RAZORPAY:
            raise BillingRuleError(
                "Subscription products are not available via Razorpay in this deployment; use Stripe or configure Razorpay plans."
            )

        if product.kind == BillingProductKind.SUBSCRIPTION:
            if provider is not PaymentProvider.STRIPE:
                raise BillingRuleError("Subscription products require Stripe checkout.")
            if not (product.stripe_price_id or "").strip():
                raise BillingRuleError("Product is missing stripe_price_id for subscription checkout.")
            checkout_mode = BillingCheckoutMode.SUBSCRIPTION
        else:
            checkout_mode = BillingCheckoutMode.PAYMENT

        if provider is PaymentProvider.RAZORPAY and int(product.amount_minor) <= 0:
            raise BillingRuleError("Product amount_minor must be positive for Razorpay orders.")

        meta = {
            "user_id": user.id,
            "product_sku": product.sku,
        }

        req = CheckoutSessionRequest(
            amount_minor=int(product.amount_minor),
            currency=product.currency.strip(),
            success_url=str(body.success_url),
            cancel_url=str(body.cancel_url),
            client_reference_id=user.id,
            title=product.title,
            metadata=meta,
            checkout_mode=checkout_mode,  # type: ignore[arg-type]
            stripe_price_id=(product.stripe_price_id or "").strip() or None,
            stripe_subscription_data_metadata={"user_id": user.id, "product_sku": product.sku},
        )

        gateway = self._factory.build(provider)
        result = gateway.create_checkout_session(req)

        row = BillingCheckoutSessionModel(
            user_id=user.id,
            product_id=product.id,
            provider=provider.value,
            provider_checkout_id=result.provider_session_id,
            status="pending",
        )
        self._db.add(row)
        self._db.commit()
        return result

    def _checkout_custom_amount(self, user: UserModel, body: PaymentCheckoutRequest) -> CheckoutSessionResult:
        provider = PaymentProvider.STRIPE if body.provider == "stripe" else PaymentProvider.RAZORPAY
        meta = {**body.metadata, "user_id": user.id}
        req = CheckoutSessionRequest(
            amount_minor=body.amount_minor,
            currency=body.currency.strip(),
            success_url=str(body.success_url),
            cancel_url=str(body.cancel_url),
            client_reference_id=user.id,
            title=body.title,
            metadata=meta,
            checkout_mode="payment",
        )
        gateway = self._factory.build(provider)
        result = gateway.create_checkout_session(req)
        row = BillingCheckoutSessionModel(
            user_id=user.id,
            product_id=None,
            provider=provider.value,
            provider_checkout_id=result.provider_session_id,
            status="pending",
        )
        self._db.add(row)
        self._db.commit()
        return result
