"""add meeting evidence bundle status

Revision ID: 20260322_0007
Revises: 20260320_0006
Create Date: 2026-03-22 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260322_0007"
down_revision = "20260320_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "meeting_evidence_bundles",
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
    )
    op.create_index(
        "ix_meeting_evidence_bundles_status",
        "meeting_evidence_bundles",
        ["status"],
        unique=False,
    )
    op.alter_column("meeting_evidence_bundles", "status", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_meeting_evidence_bundles_status", table_name="meeting_evidence_bundles")
    op.drop_column("meeting_evidence_bundles", "status")
