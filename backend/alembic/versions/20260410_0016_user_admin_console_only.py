"""add users.admin_console_only (restrict workspace API for admin-only accounts)

Revision ID: 20260410_0016
Revises: 20260410_0015
Create Date: 2026-04-10 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260410_0016"
down_revision = "20260410_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("admin_console_only", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute(sa.text("UPDATE users SET admin_console_only = true WHERE username = 'admin'"))


def downgrade() -> None:
    op.drop_column("users", "admin_console_only")
