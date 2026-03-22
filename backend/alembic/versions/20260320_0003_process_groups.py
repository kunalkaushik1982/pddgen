"""Add process groups and link steps/notes to them.

Revision ID: 20260320_0003
Revises: 20260319_0002
Create Date: 2026-03-20
"""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision = "20260320_0003"
down_revision = "20260319_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "process_groups",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(length=36),
            sa.ForeignKey("draft_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False, server_default="Process 1"),
        sa.Column("canonical_slug", sa.String(length=255), nullable=False, server_default="process-1"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("summary_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("overview_diagram_json", sa.Text(), nullable=False, server_default=""),
        sa.Column("detailed_diagram_json", sa.Text(), nullable=False, server_default=""),
    )
    op.create_index("ix_process_groups_session_id", "process_groups", ["session_id"])
    op.create_index("ix_process_groups_session_order", "process_groups", ["session_id", "display_order"])

    op.add_column("process_steps", sa.Column("process_group_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        "fk_process_steps_process_group_id",
        "process_steps",
        "process_groups",
        ["process_group_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_process_steps_process_group_id", "process_steps", ["process_group_id"])

    op.add_column("process_notes", sa.Column("process_group_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        "fk_process_notes_process_group_id",
        "process_notes",
        "process_groups",
        ["process_group_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_process_notes_process_group_id", "process_notes", ["process_group_id"])

    bind = op.get_bind()
    session_ids = [row[0] for row in bind.execute(sa.text("SELECT id FROM draft_sessions")).fetchall()]
    for session_id in session_ids:
        process_group_id = str(uuid4())
        bind.execute(
            sa.text(
                """
                INSERT INTO process_groups (
                    id, session_id, title, canonical_slug, status, display_order,
                    summary_text, overview_diagram_json, detailed_diagram_json
                )
                VALUES (
                    :id, :session_id, :title, :canonical_slug, :status, :display_order,
                    :summary_text, :overview_diagram_json, :detailed_diagram_json
                )
                """
            ),
            {
                "id": process_group_id,
                "session_id": session_id,
                "title": "Process 1",
                "canonical_slug": "process-1",
                "status": "active",
                "display_order": 1,
                "summary_text": "",
                "overview_diagram_json": "",
                "detailed_diagram_json": "",
            },
        )
        bind.execute(
            sa.text(
                "UPDATE process_steps SET process_group_id = :process_group_id "
                "WHERE session_id = :session_id AND process_group_id IS NULL"
            ),
            {"process_group_id": process_group_id, "session_id": session_id},
        )
        bind.execute(
            sa.text(
                "UPDATE process_notes SET process_group_id = :process_group_id "
                "WHERE session_id = :session_id AND process_group_id IS NULL"
            ),
            {"process_group_id": process_group_id, "session_id": session_id},
        )


def downgrade() -> None:
    op.drop_index("ix_process_notes_process_group_id", table_name="process_notes")
    op.drop_constraint("fk_process_notes_process_group_id", "process_notes", type_="foreignkey")
    op.drop_column("process_notes", "process_group_id")

    op.drop_index("ix_process_steps_process_group_id", table_name="process_steps")
    op.drop_constraint("fk_process_steps_process_group_id", "process_steps", type_="foreignkey")
    op.drop_column("process_steps", "process_group_id")

    op.drop_index("ix_process_groups_session_order", table_name="process_groups")
    op.drop_index("ix_process_groups_session_id", table_name="process_groups")
    op.drop_table("process_groups")
