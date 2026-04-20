r"""
GST breakdown (India, inclusive-of-tax amounts in minor units) and invoice issuance.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.billing_checkout_session import BillingCheckoutSessionModel
from app.models.billing_invoice import BillingInvoiceCounterModel, BillingInvoiceModel
from app.models.billing_product import BillingProductModel
from app.models.user import UserModel


def compute_inclusive_gst_split(
    *,
    amount_minor: int,
    currency: str,
    gst_rate_bps: int,
    intrastate: bool,
) -> tuple[int, int, int, int, str]:
    """Return (taxable_minor, cgst, sgst, igst, supply_type). Non-INR: no GST split."""
    cur = currency.strip().upper()
    if cur != "INR" or gst_rate_bps <= 0:
        return amount_minor, 0, 0, 0, "export_or_non_gst"

    taxable = round(amount_minor * 10000 / (10000 + gst_rate_bps))
    total_tax = amount_minor - taxable
    if intrastate:
        half = total_tax // 2
        return taxable, half, total_tax - half, 0, "intrastate"
    return taxable, 0, 0, total_tax, "interstate"


def _next_invoice_number(db: Session, *, calendar_year: int) -> str:
    stmt = (
        select(BillingInvoiceCounterModel)
        .where(BillingInvoiceCounterModel.fiscal_year == calendar_year)
        .with_for_update()
    )
    row = db.execute(stmt).scalar_one_or_none()
    if row is None:
        row = BillingInvoiceCounterModel(fiscal_year=calendar_year, last_sequence=0)
        db.add(row)
        db.flush()
    row.last_sequence = int(row.last_sequence) + 1
    seq = row.last_sequence
    return f"INV-{calendar_year}-{seq:06d}"


def issue_invoice_for_payment(
    db: Session,
    *,
    settings: Settings,
    user: UserModel,
    product: BillingProductModel | None,
    provider: str,
    provider_payment_id: str | None,
    provider_order_id: str | None,
    checkout_session: BillingCheckoutSessionModel | None,
    amount_minor: int,
    currency: str,
) -> BillingInvoiceModel | None:
    """Create a tax invoice row when enabled; skip duplicates for same provider payment id."""
    if not settings.billing_gst_invoice_enabled:
        return None
    if not provider_payment_id:
        return None

    exists = db.scalars(
        select(BillingInvoiceModel).where(
            BillingInvoiceModel.provider == provider,
            BillingInvoiceModel.provider_payment_id == provider_payment_id,
        )
    ).first()
    if exists is not None:
        return exists

    cur = currency.strip().upper()
    gst_rate_bps = int(settings.billing_default_gst_rate_bps)
    seller_state = (settings.billing_seller_state_code or "").strip()[:2]
    buyer_state = (user.billing_state_code or "").strip()[:2]
    intrastate = bool(seller_state and buyer_state and seller_state == buyer_state)
    if not buyer_state:
        intrastate = str(settings.billing_supply_default).strip().lower() == "intrastate"

    taxable, cgst, sgst, igst, supply_type = compute_inclusive_gst_split(
        amount_minor=amount_minor,
        currency=cur,
        gst_rate_bps=gst_rate_bps if cur == "INR" else 0,
        intrastate=intrastate,
    )

    line_title = product.title if product else "Payment"
    line_items = [{"description": line_title, "amount_minor": amount_minor, "currency": cur}]

    now = datetime.now(timezone.utc)
    year = now.year
    invoice_number = _next_invoice_number(db, calendar_year=year)

    inv = BillingInvoiceModel(
        id=str(uuid4()),
        user_id=user.id,
        provider=provider,
        provider_payment_id=provider_payment_id,
        provider_order_id=provider_order_id,
        checkout_session_id=checkout_session.id if checkout_session else None,
        invoice_number=invoice_number,
        issued_at=now,
        currency=cur,
        amount_minor=amount_minor,
        taxable_amount_minor=taxable,
        cgst_minor=cgst,
        sgst_minor=sgst,
        igst_minor=igst,
        gst_rate_bps=gst_rate_bps if cur == "INR" else 0,
        hsn_sac=settings.billing_default_hsn_sac.strip() or None,
        seller_gstin=(settings.billing_seller_gstin or "").strip() or None,
        seller_legal_name=(settings.billing_seller_legal_name or "").strip() or None,
        seller_address=(settings.billing_seller_address or "").strip() or None,
        buyer_gstin=(user.billing_gstin or "").strip() or None,
        buyer_legal_name=(user.billing_legal_name or "").strip() or None,
        place_of_supply_state_code=buyer_state or seller_state or None,
        supply_type=supply_type,
        line_items_json=json.dumps(line_items),
        status="issued",
        extra_json=json.dumps({"product_sku": product.sku if product else None}),
    )
    db.add(inv)
    return inv


def format_invoice_text(row: BillingInvoiceModel) -> str:
    """Human-readable GST invoice text for download (not a statutory PDF)."""
    lines = [
        "TAX INVOICE",
        f"Invoice No: {row.invoice_number}",
        f"Issued: {row.issued_at.isoformat()}",
        "",
        f"Seller: {row.seller_legal_name or '—'}",
        f"Seller GSTIN: {row.seller_gstin or '—'}",
        f"Seller address: {row.seller_address or '—'}",
        "",
        f"Buyer: {row.buyer_legal_name or '—'}",
        f"Buyer GSTIN: {row.buyer_gstin or '—'}",
        f"Place of supply (state code): {row.place_of_supply_state_code or '—'}",
        f"Supply type: {row.supply_type}",
        "",
        f"HSN/SAC: {row.hsn_sac or '—'}",
        f"Currency: {row.currency}",
        f"Total (minor units): {row.amount_minor}",
        f"Taxable value (minor units): {row.taxable_amount_minor}",
        f"CGST (minor units): {row.cgst_minor}",
        f"SGST (minor units): {row.sgst_minor}",
        f"IGST (minor units): {row.igst_minor}",
        f"GST rate (bps): {row.gst_rate_bps}",
        "",
        f"Provider: {row.provider}",
        f"Payment ref: {row.provider_payment_id or '—'}",
        f"Order ref: {row.provider_order_id or '—'}",
        f"Status: {row.status}",
        "",
        "Line items:",
        row.line_items_json,
    ]
    return "\n".join(lines) + "\n"
