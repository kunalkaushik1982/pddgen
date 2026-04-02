"""add structured metadata to action logs

Revision ID: 20260323_0009
Revises: 20260323_0008
Create Date: 2026-03-23 20:15:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260323_0009"
down_revision = "20260323_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("action_logs", sa.Column("metadata_json", sa.Text(), nullable=False, server_default=""))
    op.alter_column("action_logs", "metadata_json", server_default=None)


def downgrade() -> None:
    op.drop_column("action_logs", "metadata_json")
