"""billing catalog, checkout sessions, webhook idempotency, subscriptions

Revision ID: 20260412_0019
Revises: 20260411_0018
Create Date: 2026-04-12 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260412_0019"
down_revision = "20260411_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "billing_products",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("credits_lifetime_bonus", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("credits_daily_bonus", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("amount_minor", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("stripe_price_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_checkout_mode", sa.String(length=16), nullable=False, server_default="payment"),
        sa.Column("razorpay_plan_id", sa.String(length=255), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("extra_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_billing_products_sku", "billing_products", ["sku"], unique=True)
    op.create_index("ix_billing_products_kind", "billing_products", ["kind"], unique=False)

    op.create_table(
        "billing_checkout_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("product_id", sa.String(length=36), nullable=True),
        sa.Column("provider", sa.String(length=16), nullable=False),
        sa.Column("provider_checkout_id", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["billing_products.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_billing_checkout_sessions_user_id", "billing_checkout_sessions", ["user_id"], unique=False)
    op.create_index("ix_billing_checkout_sessions_product_id", "billing_checkout_sessions", ["product_id"], unique=False)
    op.create_index(
        "ix_billing_checkout_sessions_provider_checkout_id",
        "billing_checkout_sessions",
        ["provider_checkout_id"],
        unique=False,
    )

    op.create_table(
        "payment_webhook_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=16), nullable=False),
        sa.Column("provider_event_id", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_event_id", name="uq_payment_webhook_provider_event"),
    )
    op.create_index("ix_payment_webhook_events_provider", "payment_webhook_events", ["provider"], unique=False)

    op.create_table(
        "user_subscriptions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("product_id", sa.String(length=36), nullable=True),
        sa.Column("provider", sa.String(length=16), nullable=False),
        sa.Column("external_subscription_id", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="active"),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["billing_products.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "external_subscription_id", name="uq_user_sub_provider_ext_id"),
    )
    op.create_index("ix_user_subscriptions_user_id", "user_subscriptions", ["user_id"], unique=False)
    op.create_index("ix_user_subscriptions_product_id", "user_subscriptions", ["product_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_user_subscriptions_product_id", table_name="user_subscriptions")
    op.drop_index("ix_user_subscriptions_user_id", table_name="user_subscriptions")
    op.drop_table("user_subscriptions")
    op.drop_index("ix_payment_webhook_events_provider", table_name="payment_webhook_events")
    op.drop_table("payment_webhook_events")
    op.drop_index("ix_billing_checkout_sessions_provider_checkout_id", table_name="billing_checkout_sessions")
    op.drop_index("ix_billing_checkout_sessions_product_id", table_name="billing_checkout_sessions")
    op.drop_index("ix_billing_checkout_sessions_user_id", table_name="billing_checkout_sessions")
    op.drop_table("billing_checkout_sessions")
    op.drop_index("ix_billing_products_kind", table_name="billing_products")
    op.drop_index("ix_billing_products_sku", table_name="billing_products")
    op.drop_table("billing_products")
