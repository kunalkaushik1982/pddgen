r"""
Payment HTTP surface: authenticated checkout + provider webhooks (raw body for signatures).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_payment_gateway_factory, get_payment_webhook_processor
from app.db.session import get_db_session
from app.models.user import UserModel
from app.portability.payments import (
    CheckoutSessionRequest,
    PaymentConfigurationError,
    PaymentGatewayRejectedError,
    PaymentGatewayFactoryPort,
    PaymentProvider,
    PaymentWebhookProcessorPort,
    PaymentWebhookVerificationError,
)
from app.schemas.payments import PaymentCheckoutRequest, PaymentCheckoutResponse

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
    _db: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
    factory: Annotated[PaymentGatewayFactoryPort, Depends(get_payment_gateway_factory)],
) -> PaymentCheckoutResponse:
    """Create a Stripe Checkout session or Razorpay order (one-time payment)."""
    provider = PaymentProvider.STRIPE if body.provider == "stripe" else PaymentProvider.RAZORPAY
    try:
        gateway = factory.build(provider)
    except PaymentConfigurationError as exc:
        raise _map_http(exc) from exc

    req = CheckoutSessionRequest(
        amount_minor=body.amount_minor,
        currency=body.currency.strip(),
        success_url=str(body.success_url),
        cancel_url=str(body.cancel_url),
        client_reference_id=current_user.id,
        title=body.title,
        metadata={**body.metadata, "user_id": current_user.id},
    )
    try:
        result = gateway.create_checkout_session(req)
    except (PaymentConfigurationError, PaymentGatewayRejectedError) as exc:
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
