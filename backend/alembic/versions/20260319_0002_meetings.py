"""Add meetings and provenance links.

Revision ID: 20260319_0002
Revises: 20260318_0001
Create Date: 2026-03-19
"""

from alembic import op
import sqlalchemy as sa


revision = "20260319_0002"
down_revision = "20260318_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "meetings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(length=36),
            sa.ForeignKey("draft_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False, server_default="Meeting"),
        sa.Column("meeting_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=True),
    )
    op.create_index("ix_meetings_session_id", "meetings", ["session_id"])
    op.create_index("ix_meetings_order", "meetings", ["session_id", "order_index", "uploaded_at"])

    op.add_column("artifacts", sa.Column("meeting_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        "fk_artifacts_meeting_id",
        "artifacts",
        "meetings",
        ["meeting_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_artifacts_meeting_id", "artifacts", ["meeting_id"])

    op.add_column("process_steps", sa.Column("meeting_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        "fk_process_steps_meeting_id",
        "process_steps",
        "meetings",
        ["meeting_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_process_steps_meeting_id", "process_steps", ["meeting_id"])

    op.add_column("process_notes", sa.Column("meeting_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        "fk_process_notes_meeting_id",
        "process_notes",
        "meetings",
        ["meeting_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_process_notes_meeting_id", "process_notes", ["meeting_id"])


def downgrade() -> None:
    op.drop_index("ix_process_notes_meeting_id", table_name="process_notes")
    op.drop_constraint("fk_process_notes_meeting_id", "process_notes", type_="foreignkey")
    op.drop_column("process_notes", "meeting_id")

    op.drop_index("ix_process_steps_meeting_id", table_name="process_steps")
    op.drop_constraint("fk_process_steps_meeting_id", "process_steps", type_="foreignkey")
    op.drop_column("process_steps", "meeting_id")

    op.drop_index("ix_artifacts_meeting_id", table_name="artifacts")
    op.drop_constraint("fk_artifacts_meeting_id", "artifacts", type_="foreignkey")
    op.drop_column("artifacts", "meeting_id")

    op.drop_index("ix_meetings_order", table_name="meetings")
    op.drop_index("ix_meetings_session_id", table_name="meetings")
    op.drop_table("meetings")

