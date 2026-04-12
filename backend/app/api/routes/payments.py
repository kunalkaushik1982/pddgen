r"""
Payment HTTP surface: authenticated checkout + provider webhooks (raw body for signatures).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_billing_checkout_service,
    get_current_user,
    get_payment_gateway_factory,
    get_payment_webhook_processor,
)
from app.db.session import get_db_session
from app.models.user import UserModel
from app.portability.payments import (
    PaymentConfigurationError,
    PaymentGatewayRejectedError,
    PaymentGatewayFactoryPort,
    PaymentProvider,
    PaymentWebhookProcessorPort,
    PaymentWebhookVerificationError,
)
from app.schemas.payments import PaymentCheckoutRequest, PaymentCheckoutResponse
from app.services.billing_checkout_service import BillingCheckoutService
from app.services.billing_exceptions import BillingProductNotFoundError, BillingRuleError

router = APIRouter(prefix="/payments", tags=["payments"])


def _map_http(exc: Exception) -> HTTPException:
    if isinstance(exc, PaymentConfigurationError):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    if isinstance(exc, PaymentGatewayRejectedError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if isinstance(exc, PaymentWebhookVerificationError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Payment error.")


@router.post("/checkout", response_model=PaymentCheckoutResponse)
def create_checkout(
    body: PaymentCheckoutRequest,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    billing: Annotated[BillingCheckoutService, Depends(get_billing_checkout_service)],
) -> PaymentCheckoutResponse:
    """Create a Stripe Checkout session or Razorpay order (catalog SKU or custom amount)."""
    try:
        result = billing.create_checkout(current_user, body)
    except BillingProductNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Billing product not found: {exc.sku}",
        ) from exc
    except BillingRuleError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PaymentConfigurationError as exc:
        raise _map_http(exc) from exc
    except PaymentGatewayRejectedError as exc:
        raise _map_http(exc) from exc

    return PaymentCheckoutResponse(
        provider=result.provider.value,
        provider_session_id=result.provider_session_id,
        redirect_url=result.redirect_url,
        client_payload=result.client_payload,
    )


@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    factory: Annotated[PaymentGatewayFactoryPort, Depends(get_payment_gateway_factory)],
    processor: Annotated[PaymentWebhookProcessorPort, Depends(get_payment_webhook_processor)],
) -> Response:
    raw = await request.body()
    headers = {k: v for k, v in request.headers.items()}
    try:
        gateway = factory.build(PaymentProvider.STRIPE)
        event = gateway.verify_and_parse_webhook(raw_body=raw, headers=headers)
    except PaymentConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except PaymentWebhookVerificationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    processor.process(event)
    return Response(status_code=status.HTTP_200_OK)


@router.post("/webhooks/razorpay")
async def razorpay_webhook(
    request: Request,
    factory: Annotated[PaymentGatewayFactoryPort, Depends(get_payment_gateway_factory)],
    processor: Annotated[PaymentWebhookProcessorPort, Depends(get_payment_webhook_processor)],
) -> Response:
    raw = await request.body()
    headers = {k: v for k, v in request.headers.items()}
    try:
        gateway = factory.build(PaymentProvider.RAZORPAY)
        event = gateway.verify_and_parse_webhook(raw_body=raw, headers=headers)
    except PaymentConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except PaymentWebhookVerificationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    processor.process(event)
    return Response(status_code=status.HTTP_200_OK)
