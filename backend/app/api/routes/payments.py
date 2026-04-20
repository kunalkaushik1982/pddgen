r"""
Payment HTTP surface: authenticated checkout + provider webhooks (raw body for signatures).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_billing_checkout_service,
    get_current_user,
    get_payment_gateway_factory,
    get_payment_webhook_processor,
)
from app.core.config import get_settings
from app.db.session import get_db_session
from app.models.billing_invoice import BillingInvoiceModel
from app.models.billing_product import BillingProductModel
from app.models.user import UserModel
from app.portability.payments import (
    PaymentConfigurationError,
    PaymentGatewayRejectedError,
    PaymentGatewayFactoryPort,
    PaymentProvider,
    PaymentWebhookProcessorPort,
    PaymentWebhookVerificationError,
)
from app.schemas.billing import BillingProductPublic
from app.schemas.billing_compliance import BillingInvoiceDetail, BillingInvoicePublic, BillingProfilePatchRequest
from app.schemas.payments import PaymentCheckoutRequest, PaymentCheckoutResponse
from app.services.billing.billing_catalog_mapper import to_public
from app.services.billing.billing_checkout_service import BillingCheckoutService
from app.services.billing.billing_exceptions import BillingProductNotFoundError, BillingRuleError
from app.services.billing.gst_invoice_service import format_invoice_text

router = APIRouter(prefix="/payments", tags=["payments"])


def _map_http(exc: Exception) -> HTTPException:
    if isinstance(exc, PaymentConfigurationError):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    if isinstance(exc, PaymentGatewayRejectedError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if isinstance(exc, PaymentWebhookVerificationError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Payment error.")


@router.get("/public-config")
def get_payment_public_config() -> dict[str, str | bool | None]:
    """Publishable provider keys for client-side checkout (safe to expose)."""
    settings = get_settings()
    return {
        "razorpay_key_id": settings.payment_razorpay_key_id.strip() or None,
        "stripe_publishable_key": settings.payment_stripe_publishable_key.strip() or None,
        "billing_gst_invoice_enabled": bool(settings.billing_gst_invoice_enabled),
    }


@router.get("/products", response_model=list[BillingProductPublic])
def list_billing_products(
    db: Annotated[Session, Depends(get_db_session)],
    _current_user: Annotated[UserModel, Depends(get_current_user)],
) -> list[BillingProductPublic]:
    """Active catalog products for the authenticated checkout UI."""
    rows = list(db.execute(select(BillingProductModel).where(BillingProductModel.active.is_(True)).order_by(BillingProductModel.sku)).scalars().all())
    return [to_public(row) for row in rows]


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


@router.patch("/billing-profile", status_code=204)
def patch_billing_profile(
    body: BillingProfilePatchRequest,
    db: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> Response:
    """Optional GSTIN / legal name / state for tax invoices."""
    if body.billing_gstin is not None:
        current_user.billing_gstin = body.billing_gstin.strip() or None
    if body.billing_legal_name is not None:
        current_user.billing_legal_name = body.billing_legal_name.strip() or None
    if body.billing_state_code is not None:
        current_user.billing_state_code = body.billing_state_code.strip().upper()[:2] or None
    db.add(current_user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _invoice_to_public(row: BillingInvoiceModel) -> BillingInvoicePublic:
    return BillingInvoicePublic(
        id=row.id,
        invoice_number=row.invoice_number,
        issued_at=row.issued_at,
        currency=row.currency,
        amount_minor=int(row.amount_minor),
        taxable_amount_minor=int(row.taxable_amount_minor),
        cgst_minor=int(row.cgst_minor),
        sgst_minor=int(row.sgst_minor),
        igst_minor=int(row.igst_minor),
        status=row.status,
        provider=row.provider,
    )


def _invoice_to_detail(row: BillingInvoiceModel) -> BillingInvoiceDetail:
    base = _invoice_to_public(row)
    return BillingInvoiceDetail(
        **base.model_dump(),
        gst_rate_bps=int(row.gst_rate_bps),
        hsn_sac=row.hsn_sac,
        seller_gstin=row.seller_gstin,
        seller_legal_name=row.seller_legal_name,
        buyer_gstin=row.buyer_gstin,
        buyer_legal_name=row.buyer_legal_name,
        place_of_supply_state_code=row.place_of_supply_state_code,
        supply_type=row.supply_type,
        line_items_json=row.line_items_json,
        provider_payment_id=row.provider_payment_id,
        provider_order_id=row.provider_order_id,
    )


@router.get("/invoices", response_model=list[BillingInvoicePublic])
def list_my_invoices(
    db: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> list[BillingInvoicePublic]:
    rows = list(
        db.execute(
            select(BillingInvoiceModel)
            .where(BillingInvoiceModel.user_id == current_user.id)
            .order_by(BillingInvoiceModel.issued_at.desc())
        )
        .scalars()
        .all()
    )
    return [_invoice_to_public(r) for r in rows]


@router.get("/invoices/{invoice_id}", response_model=BillingInvoiceDetail)
def get_my_invoice(
    invoice_id: str,
    db: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> BillingInvoiceDetail:
    row = db.get(BillingInvoiceModel, invoice_id)
    if row is None or row.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found.")
    return _invoice_to_detail(row)


@router.get("/invoices/{invoice_id}/document")
def download_invoice_document(
    invoice_id: str,
    db: Annotated[Session, Depends(get_db_session)],
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> PlainTextResponse:
    row = db.get(BillingInvoiceModel, invoice_id)
    if row is None or row.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found.")
    text = format_invoice_text(row)
    return PlainTextResponse(
        content=text,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'inline; filename="invoice-{row.invoice_number}.txt"'},
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
