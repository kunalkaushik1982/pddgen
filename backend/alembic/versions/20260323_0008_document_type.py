"""add document type to draft sessions

Revision ID: 20260323_0008
Revises: 20260322_0007
Create Date: 2026-03-23 14:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260323_0008"
down_revision = "20260322_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("draft_sessions", sa.Column("document_type", sa.String(length=50), nullable=False, server_default="pdd"))
    op.alter_column("draft_sessions", "document_type", server_default=None)


def downgrade() -> None:
    op.drop_column("draft_sessions", "document_type")
