"""llm usage events and background job run metrics

Revision ID: 20260410_0014
Revises: 20260408_0013
Create Date: 2026-04-10 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260410_0014"
down_revision = "20260408_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_usage_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=255), nullable=False),
        sa.Column("skill_id", sa.String(length=128), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost_usd", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["draft_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_llm_usage_events_session_id"), "llm_usage_events", ["session_id"], unique=False)
    op.create_index(op.f("ix_llm_usage_events_owner_id"), "llm_usage_events", ["owner_id"], unique=False)
    op.create_index(op.f("ix_llm_usage_events_created_at"), "llm_usage_events", ["created_at"], unique=False)

    op.create_table(
        "background_job_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=255), nullable=False),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("celery_task_id", sa.String(length=255), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["draft_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_background_job_runs_session_id"), "background_job_runs", ["session_id"], unique=False)
    op.create_index(op.f("ix_background_job_runs_owner_id"), "background_job_runs", ["owner_id"], unique=False)
    op.create_index(op.f("ix_background_job_runs_created_at"), "background_job_runs", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_background_job_runs_created_at"), table_name="background_job_runs")
    op.drop_index(op.f("ix_background_job_runs_owner_id"), table_name="background_job_runs")
    op.drop_index(op.f("ix_background_job_runs_session_id"), table_name="background_job_runs")
    op.drop_table("background_job_runs")

    op.drop_index(op.f("ix_llm_usage_events_created_at"), table_name="llm_usage_events")
    op.drop_index(op.f("ix_llm_usage_events_owner_id"), table_name="llm_usage_events")
    op.drop_index(op.f("ix_llm_usage_events_session_id"), table_name="llm_usage_events")
    op.drop_table("llm_usage_events")
