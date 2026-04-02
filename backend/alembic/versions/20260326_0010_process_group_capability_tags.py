"""add capability tags json to process groups

Revision ID: 20260326_0010
Revises: 20260323_0009
Create Date: 2026-03-26 21:15:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260326_0010"
down_revision = "20260323_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("process_groups", sa.Column("capability_tags_json", sa.Text(), nullable=False, server_default="[]"))
    op.alter_column("process_groups", "capability_tags_json", server_default=None)


def downgrade() -> None:
    op.drop_column("process_groups", "capability_tags_json")
