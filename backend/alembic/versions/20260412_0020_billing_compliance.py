"""GST invoices, refunds, disputes, user billing profile fields

Revision ID: 20260412_0020
Revises: 20260412_0019
Create Date: 2026-04-12 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260412_0020"
down_revision = "20260412_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("billing_gstin", sa.String(length=15), nullable=True))
    op.add_column("users", sa.Column("billing_legal_name", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("billing_state_code", sa.String(length=2), nullable=True))

    op.create_table(
        "billing_invoice_counters",
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("last_sequence", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("fiscal_year"),
    )

    op.create_table(
        "billing_invoices",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=16), nullable=False),
        sa.Column("provider_payment_id", sa.String(length=255), nullable=True),
        sa.Column("provider_order_id", sa.String(length=255), nullable=True),
        sa.Column("checkout_session_id", sa.String(length=36), nullable=True),
        sa.Column("invoice_number", sa.String(length=32), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("taxable_amount_minor", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cgst_minor", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sgst_minor", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("igst_minor", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("gst_rate_bps", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("hsn_sac", sa.String(length=16), nullable=True),
        sa.Column("seller_gstin", sa.String(length=15), nullable=True),
        sa.Column("seller_legal_name", sa.String(length=255), nullable=True),
        sa.Column("seller_address", sa.Text(), nullable=True),
        sa.Column("buyer_gstin", sa.String(length=15), nullable=True),
        sa.Column("buyer_legal_name", sa.String(length=255), nullable=True),
        sa.Column("place_of_supply_state_code", sa.String(length=2), nullable=True),
        sa.Column("supply_type", sa.String(length=24), nullable=False, server_default="intrastate"),
        sa.Column("line_items_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="issued"),
        sa.Column("extra_json", sa.Text(), nullable=False, server_default="{}"),
        sa.ForeignKeyConstraint(["checkout_session_id"], ["billing_checkout_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_payment_id", name="uq_billing_invoice_provider_payment"),
    )
    op.create_index("ix_billing_invoices_user_id", "billing_invoices", ["user_id"], unique=False)
    op.create_index("ix_billing_invoices_invoice_number", "billing_invoices", ["invoice_number"], unique=True)

    op.create_table(
        "billing_refunds",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("provider", sa.String(length=16), nullable=False),
        sa.Column("provider_refund_id", sa.String(length=255), nullable=False),
        sa.Column("provider_payment_id", sa.String(length=255), nullable=True),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.String(length=512), nullable=True),
        sa.Column("initiated_by", sa.String(length=16), nullable=False, server_default="webhook"),
        sa.Column("raw_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_refund_id", name="uq_billing_refund_provider"),
    )
    op.create_index("ix_billing_refunds_user_id", "billing_refunds", ["user_id"], unique=False)

    op.create_table(
        "billing_disputes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("provider", sa.String(length=16), nullable=False),
        sa.Column("provider_dispute_id", sa.String(length=255), nullable=False),
        sa.Column("provider_payment_id", sa.String(length=255), nullable=True),
        sa.Column("amount_minor", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("status", sa.String(length=48), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_dispute_id", name="uq_billing_dispute_provider"),
    )
    op.create_index("ix_billing_disputes_user_id", "billing_disputes", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_billing_disputes_user_id", table_name="billing_disputes")
    op.drop_table("billing_disputes")
    op.drop_index("ix_billing_refunds_user_id", table_name="billing_refunds")
    op.drop_table("billing_refunds")
    op.drop_index("ix_billing_invoices_invoice_number", table_name="billing_invoices")
    op.drop_index("ix_billing_invoices_user_id", table_name="billing_invoices")
    op.drop_table("billing_invoices")
    op.drop_table("billing_invoice_counters")
    op.drop_column("users", "billing_state_code")
    op.drop_column("users", "billing_legal_name")
    op.drop_column("users", "billing_gstin")
