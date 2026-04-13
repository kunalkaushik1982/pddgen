r"""
DTOs for GST invoices, refunds, disputes, and billing profile.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class BillingInvoicePublic(BaseModel):
    id: str
    invoice_number: str
    issued_at: datetime
    currency: str
    amount_minor: int
    taxable_amount_minor: int
    cgst_minor: int
    sgst_minor: int
    igst_minor: int
    status: str
    provider: str


class BillingInvoiceDetail(BillingInvoicePublic):
    gst_rate_bps: int
    hsn_sac: str | None
    seller_gstin: str | None
    seller_legal_name: str | None
    buyer_gstin: str | None
    buyer_legal_name: str | None
    place_of_supply_state_code: str | None
    supply_type: str
    line_items_json: str
    provider_payment_id: str | None
    provider_order_id: str | None


class BillingRefundPublic(BaseModel):
    id: str
    user_id: str | None
    provider: str
    provider_refund_id: str
    provider_payment_id: str | None
    amount_minor: int
    currency: str
    status: str
    initiated_by: str
    created_at: datetime


class BillingDisputePublic(BaseModel):
    id: str
    user_id: str | None
    provider: str
    provider_dispute_id: str
    provider_payment_id: str | None
    amount_minor: int | None
    currency: str | None
    status: str
    reason_code: str | None
    opened_at: datetime | None
    closed_at: datetime | None
    created_at: datetime


class BillingProfilePatchRequest(BaseModel):
    billing_gstin: str | None = Field(default=None, max_length=15)
    billing_legal_name: str | None = Field(default=None, max_length=255)
    billing_state_code: str | None = Field(default=None, max_length=2)


class AdminRefundInitiateRequest(BaseModel):
    provider: Literal["stripe", "razorpay"]
    provider_payment_id: str = Field(min_length=8, max_length=255)
    amount_minor: int | None = Field(default=None, ge=1)
    notes: str | None = Field(default=None, max_length=500)
