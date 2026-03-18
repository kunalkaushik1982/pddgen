"""Create baseline application schema.

Revision ID: 20260318_0001
Revises:
Create Date: 2026-03-18 20:45:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260318_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "draft_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("owner_id", sa.String(length=255), nullable=False),
        sa.Column("diagram_type", sa.String(length=50), nullable=False),
        sa.Column("overview_diagram_json", sa.Text(), nullable=False),
        sa.Column("detailed_diagram_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_draft_sessions_status"), "draft_sessions", ["status"], unique=False)

    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    op.create_table(
        "action_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("actor", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["draft_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_action_logs_created_at"), "action_logs", ["created_at"], unique=False)
    op.create_index(op.f("ix_action_logs_session_id"), "action_logs", ["session_id"], unique=False)

    op.create_table(
        "artifacts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["draft_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_artifacts_kind"), "artifacts", ["kind"], unique=False)
    op.create_index(op.f("ix_artifacts_session_id"), "artifacts", ["session_id"], unique=False)

    op.create_table(
        "diagram_layouts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("view_type", sa.String(), nullable=False),
        sa.Column("layout_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["draft_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_diagram_layouts_session_id"), "diagram_layouts", ["session_id"], unique=False)
    op.create_index(op.f("ix_diagram_layouts_view_type"), "diagram_layouts", ["view_type"], unique=False)

    op.create_table(
        "output_documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("exported_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["draft_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_output_documents_session_id"), "output_documents", ["session_id"], unique=False)

    op.create_table(
        "process_notes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("related_step_ids", sa.Text(), nullable=False),
        sa.Column("evidence_reference_ids", sa.Text(), nullable=False),
        sa.Column("confidence", sa.String(length=20), nullable=False),
        sa.Column("inference_type", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["draft_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_process_notes_session_id"), "process_notes", ["session_id"], unique=False)

    op.create_table(
        "process_steps",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("application_name", sa.String(length=255), nullable=False),
        sa.Column("action_text", sa.Text(), nullable=False),
        sa.Column("source_data_note", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.String(length=50), nullable=False),
        sa.Column("start_timestamp", sa.String(length=50), nullable=False),
        sa.Column("end_timestamp", sa.String(length=50), nullable=False),
        sa.Column("supporting_transcript_text", sa.Text(), nullable=False),
        sa.Column("screenshot_id", sa.String(length=36), nullable=False),
        sa.Column("confidence", sa.String(length=20), nullable=False),
        sa.Column("evidence_references", sa.Text(), nullable=False),
        sa.Column("edited_by_ba", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["draft_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_process_steps_session_id"), "process_steps", ["session_id"], unique=False)
    op.create_index(op.f("ix_process_steps_step_number"), "process_steps", ["step_number"], unique=False)

    op.create_table(
        "user_auth_tokens",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_auth_tokens_expires_at"), "user_auth_tokens", ["expires_at"], unique=False)
    op.create_index(op.f("ix_user_auth_tokens_token_hash"), "user_auth_tokens", ["token_hash"], unique=True)
    op.create_index(op.f("ix_user_auth_tokens_user_id"), "user_auth_tokens", ["user_id"], unique=False)

    op.create_table(
        "process_step_screenshot_candidates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("step_id", sa.String(length=36), nullable=False),
        sa.Column("artifact_id", sa.String(length=36), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.String(length=50), nullable=False),
        sa.Column("source_role", sa.String(length=20), nullable=False),
        sa.Column("selection_method", sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(["artifact_id"], ["artifacts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["step_id"], ["process_steps.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_process_step_screenshot_candidates_artifact_id"),
        "process_step_screenshot_candidates",
        ["artifact_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_process_step_screenshot_candidates_step_id"),
        "process_step_screenshot_candidates",
        ["step_id"],
        unique=False,
    )

    op.create_table(
        "process_step_screenshots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("step_id", sa.String(length=36), nullable=False),
        sa.Column("artifact_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.String(length=50), nullable=False),
        sa.Column("selection_method", sa.String(length=50), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["artifact_id"], ["artifacts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["step_id"], ["process_steps.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_process_step_screenshots_artifact_id"),
        "process_step_screenshots",
        ["artifact_id"],
        unique=False,
    )
    op.create_index(op.f("ix_process_step_screenshots_step_id"), "process_step_screenshots", ["step_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_process_step_screenshots_step_id"), table_name="process_step_screenshots")
    op.drop_index(op.f("ix_process_step_screenshots_artifact_id"), table_name="process_step_screenshots")
    op.drop_table("process_step_screenshots")

    op.drop_index(op.f("ix_process_step_screenshot_candidates_step_id"), table_name="process_step_screenshot_candidates")
    op.drop_index(
        op.f("ix_process_step_screenshot_candidates_artifact_id"),
        table_name="process_step_screenshot_candidates",
    )
    op.drop_table("process_step_screenshot_candidates")

    op.drop_index(op.f("ix_user_auth_tokens_user_id"), table_name="user_auth_tokens")
    op.drop_index(op.f("ix_user_auth_tokens_token_hash"), table_name="user_auth_tokens")
    op.drop_index(op.f("ix_user_auth_tokens_expires_at"), table_name="user_auth_tokens")
    op.drop_table("user_auth_tokens")

    op.drop_index(op.f("ix_process_steps_step_number"), table_name="process_steps")
    op.drop_index(op.f("ix_process_steps_session_id"), table_name="process_steps")
    op.drop_table("process_steps")

    op.drop_index(op.f("ix_process_notes_session_id"), table_name="process_notes")
    op.drop_table("process_notes")

    op.drop_index(op.f("ix_output_documents_session_id"), table_name="output_documents")
    op.drop_table("output_documents")

    op.drop_index(op.f("ix_diagram_layouts_view_type"), table_name="diagram_layouts")
    op.drop_index(op.f("ix_diagram_layouts_session_id"), table_name="diagram_layouts")
    op.drop_table("diagram_layouts")

    op.drop_index(op.f("ix_artifacts_session_id"), table_name="artifacts")
    op.drop_index(op.f("ix_artifacts_kind"), table_name="artifacts")
    op.drop_table("artifacts")

    op.drop_index(op.f("ix_action_logs_session_id"), table_name="action_logs")
    op.drop_index(op.f("ix_action_logs_created_at"), table_name="action_logs")
    op.drop_table("action_logs")

    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_table("users")

    op.drop_index(op.f("ix_draft_sessions_status"), table_name="draft_sessions")
    op.drop_table("draft_sessions")
