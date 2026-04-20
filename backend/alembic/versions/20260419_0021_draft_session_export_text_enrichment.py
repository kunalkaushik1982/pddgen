"""Add export_text_enrichment_json to draft_sessions for batched LLM narrative.

Revision ID: 20260419_0021
Revises: 20260412_0020
Create Date: 2026-04-19
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260419_0021"
down_revision = "20260412_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "draft_sessions",
        sa.Column("export_text_enrichment_json", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("draft_sessions", "export_text_enrichment_json")
