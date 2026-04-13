r"""
GST / tax invoice rows issued for successful payments.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class BillingInvoiceCounterModel(Base):
    """Per-calendar-year sequence for invoice numbers (row locked when allocating)."""

    __tablename__ = "billing_invoice_counters"

    fiscal_year: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class BillingInvoiceModel(Base):
    __tablename__ = "billing_invoices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(16), nullable=False)
    provider_payment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_order_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    checkout_session_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("billing_checkout_sessions.id", ondelete="SET NULL"), nullable=True
    )
    invoice_number: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    taxable_amount_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cgst_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sgst_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    igst_minor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    gst_rate_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hsn_sac: Mapped[str | None] = mapped_column(String(16), nullable=True)
    seller_gstin: Mapped[str | None] = mapped_column(String(15), nullable=True)
    seller_legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    seller_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    buyer_gstin: Mapped[str | None] = mapped_column(String(15), nullable=True)
    buyer_legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    place_of_supply_state_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    supply_type: Mapped[str] = mapped_column(String(24), nullable=False, default="intrastate")
    line_items_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="issued")
    extra_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    user: Mapped["UserModel"] = relationship()  # noqa: F821
