r"""
Admin CRUD for ``billing_products`` (catalog).
"""

from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_admin_user
from app.core.config import get_settings
from app.db.session import get_db_session
from app.models.billing_dispute import BillingDisputeModel
from app.models.billing_invoice import BillingInvoiceModel
from app.models.billing_product import BillingProductModel
from app.models.billing_refund import BillingRefundModel
from app.models.user import UserModel
from app.schemas.billing import (
    BillingProductAdminResponse,
    BillingProductCreateRequest,
    BillingProductUpdateRequest,
)
from app.schemas.billing_compliance import (
    AdminRefundInitiateRequest,
    BillingDisputePublic,
    BillingInvoiceDetail,
    BillingRefundPublic,
)
from app.services.billing_refund_initiation_service import BillingRefundInitiationError, initiate_provider_refund

router = APIRouter(prefix="/admin/billing", tags=["admin-billing"])


def _to_admin(row: BillingProductModel) -> BillingProductAdminResponse:
    return BillingProductAdminResponse(
        id=row.id,
        sku=row.sku,
        kind=row.kind,
        title=row.title,
        credits_lifetime_bonus=int(row.credits_lifetime_bonus),
        credits_daily_bonus=int(row.credits_daily_bonus),
        amount_minor=int(row.amount_minor),
        currency=row.currency,
        stripe_price_id=row.stripe_price_id,
        stripe_checkout_mode=row.stripe_checkout_mode,
        razorpay_plan_id=row.razorpay_plan_id,
        active=bool(row.active),
        extra_json=row.extra_json or "{}",
    )


@router.get("/products", response_model=list[BillingProductAdminResponse])
def admin_list_billing_products(
    db: Annotated[Session, Depends(get_db_session)],
    _admin: Annotated[UserModel, Depends(get_current_admin_user)],
) -> list[BillingProductAdminResponse]:
    rows = list(db.execute(select(BillingProductModel).order_by(BillingProductModel.sku)).scalars().all())
    return [_to_admin(r) for r in rows]


@router.post("/products", response_model=BillingProductAdminResponse)
def admin_create_billing_product(
    body: BillingProductCreateRequest,
    db: Annotated[Session, Depends(get_db_session)],
    _admin: Annotated[UserModel, Depends(get_current_admin_user)],
) -> BillingProductAdminResponse:
    exists = db.scalars(select(BillingProductModel).where(BillingProductModel.sku == body.sku)).first()
    if exists is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A product with this SKU already exists.")
    row = BillingProductModel(
        id=str(uuid4()),
        sku=body.sku.strip(),
        kind=body.kind.strip(),
        title=body.title.strip(),
        credits_lifetime_bonus=body.credits_lifetime_bonus,
        credits_daily_bonus=body.credits_daily_bonus,
        amount_minor=body.amount_minor,
        currency=body.currency.strip().upper(),
        stripe_price_id=(body.stripe_price_id or "").strip() or None,
        stripe_checkout_mode=body.stripe_checkout_mode.strip(),
        razorpay_plan_id=(body.razorpay_plan_id or "").strip() or None,
        active=body.active,
        extra_json=body.extra_json.strip() or "{}",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_admin(row)


@router.patch("/products/{product_id}", response_model=BillingProductAdminResponse)
def admin_update_billing_product(
    product_id: str,
    body: BillingProductUpdateRequest,
    db: Annotated[Session, Depends(get_db_session)],
    _admin: Annotated[UserModel, Depends(get_current_admin_user)],
) -> BillingProductAdminResponse:
    row = db.get(BillingProductModel, product_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    data = body.model_dump(exclude_unset=True)
    if "currency" in data and data["currency"] is not None:
        data["currency"] = str(data["currency"]).strip().upper()
    if "stripe_price_id" in data:
        data["stripe_price_id"] = (data["stripe_price_id"] or "").strip() or None
    if "razorpay_plan_id" in data:
        data["razorpay_plan_id"] = (data["razorpay_plan_id"] or "").strip() or None
    if "stripe_checkout_mode" in data and data["stripe_checkout_mode"] is not None:
        data["stripe_checkout_mode"] = str(data["stripe_checkout_mode"]).strip()
    if "kind" in data and data["kind"] is not None:
        data["kind"] = str(data["kind"]).strip()
    if "title" in data and data["title"] is not None:
        data["title"] = str(data["title"]).strip()
    if "extra_json" in data and data["extra_json"] is not None:
        data["extra_json"] = str(data["extra_json"]).strip() or "{}"
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return _to_admin(row)


@router.delete("/products/{product_id}")
def admin_delete_billing_product(
    product_id: str,
    db: Annotated[Session, Depends(get_db_session)],
    _admin: Annotated[UserModel, Depends(get_current_admin_user)],
) -> Response:
    row = db.get(BillingProductModel, product_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    row.active = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _invoice_to_detail_admin(row: BillingInvoiceModel) -> BillingInvoiceDetail:
    return BillingInvoiceDetail(
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


@router.get("/invoices", response_model=list[BillingInvoiceDetail])
def admin_list_invoices(
    db: Annotated[Session, Depends(get_db_session)],
    _admin: Annotated[UserModel, Depends(get_current_admin_user)],
) -> list[BillingInvoiceDetail]:
    rows = list(
        db.execute(select(BillingInvoiceModel).order_by(BillingInvoiceModel.issued_at.desc()).limit(500)).scalars().all()
    )
    return [_invoice_to_detail_admin(r) for r in rows]


@router.get("/refunds", response_model=list[BillingRefundPublic])
def admin_list_refunds(
    db: Annotated[Session, Depends(get_db_session)],
    _admin: Annotated[UserModel, Depends(get_current_admin_user)],
) -> list[BillingRefundPublic]:
    rows = list(
        db.execute(select(BillingRefundModel).order_by(BillingRefundModel.created_at.desc()).limit(500)).scalars().all()
    )
    return [
        BillingRefundPublic(
            id=r.id,
            user_id=r.user_id,
            provider=r.provider,
            provider_refund_id=r.provider_refund_id,
            provider_payment_id=r.provider_payment_id,
            amount_minor=int(r.amount_minor),
            currency=r.currency,
            status=r.status,
            initiated_by=r.initiated_by,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.get("/disputes", response_model=list[BillingDisputePublic])
def admin_list_disputes(
    db: Annotated[Session, Depends(get_db_session)],
    _admin: Annotated[UserModel, Depends(get_current_admin_user)],
) -> list[BillingDisputePublic]:
    rows = list(
        db.execute(select(BillingDisputeModel).order_by(BillingDisputeModel.created_at.desc()).limit(500)).scalars().all()
    )
    return [
        BillingDisputePublic(
            id=r.id,
            user_id=r.user_id,
            provider=r.provider,
            provider_dispute_id=r.provider_dispute_id,
            provider_payment_id=r.provider_payment_id,
            amount_minor=r.amount_minor,
            currency=r.currency,
            status=r.status,
            reason_code=r.reason_code,
            opened_at=r.opened_at,
            closed_at=r.closed_at,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post("/refunds/initiate")
def admin_initiate_refund(
    body: AdminRefundInitiateRequest,
    _db: Annotated[Session, Depends(get_db_session)],
    _admin: Annotated[UserModel, Depends(get_current_admin_user)],
) -> dict[str, object]:
    settings = get_settings()
    try:
        result = initiate_provider_refund(
            settings,
            provider=body.provider,
            provider_payment_id=body.provider_payment_id.strip(),
            amount_minor=body.amount_minor,
            notes=body.notes,
        )
    except BillingRefundInitiationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
    rid = result.get("id") if isinstance(result, dict) else None
    return {"ok": True, "provider_refund_id": rid, "raw": result}
