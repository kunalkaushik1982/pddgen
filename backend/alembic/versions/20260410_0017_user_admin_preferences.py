"""add users.admin_preferences_json for persisted admin console preferences

Revision ID: 20260410_0017
Revises: 20260410_0016
Create Date: 2026-04-10 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260410_0017"
down_revision = "20260410_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("admin_preferences_json", sa.Text(), nullable=False, server_default=""),
    )
    op.alter_column("users", "admin_preferences_json", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "admin_preferences_json")
