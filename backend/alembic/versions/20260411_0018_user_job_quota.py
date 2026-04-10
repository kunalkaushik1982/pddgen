"""user job quota (lifetime/daily usage and admin bonuses)

Revision ID: 20260411_0018
Revises: 20260410_0017
Create Date: 2026-04-11 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260411_0018"
down_revision = "20260410_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("quota_lifetime_bonus", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column("quota_daily_bonus", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column("job_usage_lifetime", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column("job_usage_daily", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("users", sa.Column("job_usage_daily_date", sa.Date(), nullable=True))
    for col in (
        "quota_lifetime_bonus",
        "quota_daily_bonus",
        "job_usage_lifetime",
        "job_usage_daily",
    ):
        op.alter_column("users", col, server_default=None)

    op.execute(
        sa.text(
            """
            UPDATE users AS u
            SET job_usage_lifetime = COALESCE((
                SELECT COUNT(*)::integer FROM draft_sessions ds WHERE ds.owner_id = u.username
            ), 0) + COALESCE((
                SELECT COUNT(*)::integer
                FROM action_logs al
                INNER JOIN draft_sessions ds2 ON ds2.id = al.session_id
                WHERE ds2.owner_id = u.username
                AND al.event_type IN ('generation_queued', 'screenshot_generation_queued')
            ), 0)
            """
        )
    )


def downgrade() -> None:
    op.drop_column("users", "job_usage_daily_date")
    op.drop_column("users", "job_usage_daily")
    op.drop_column("users", "job_usage_lifetime")
    op.drop_column("users", "quota_daily_bonus")
    op.drop_column("users", "quota_lifetime_bonus")
