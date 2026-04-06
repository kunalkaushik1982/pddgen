"""generation wall time columns on draft_sessions

Revision ID: 20260406_0011
Revises: 20260326_0010
Create Date: 2026-04-06 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260406_0011"
down_revision = "20260326_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("draft_sessions", sa.Column("draft_generation_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("draft_sessions", sa.Column("draft_generation_completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("draft_sessions", sa.Column("screenshot_generation_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("draft_sessions", sa.Column("screenshot_generation_completed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("draft_sessions", "screenshot_generation_completed_at")
    op.drop_column("draft_sessions", "screenshot_generation_started_at")
    op.drop_column("draft_sessions", "draft_generation_completed_at")
    op.drop_column("draft_sessions", "draft_generation_started_at")
