"""Widen process_notes.inference_type for LLM-derived labels (e.g. platform_integration).

Revision ID: 20260420_0022
Revises: 20260419_0021
Create Date: 2026-04-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260420_0022"
down_revision = "20260419_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "process_notes",
        "inference_type",
        existing_type=sa.String(length=20),
        type_=sa.String(length=128),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "process_notes",
        "inference_type",
        existing_type=sa.String(length=128),
        type_=sa.String(length=20),
        existing_nullable=False,
    )
