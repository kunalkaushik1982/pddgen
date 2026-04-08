"""add user password reset token table

Revision ID: 20260408_0012
Revises: 20260406_0011
Create Date: 2026-04-08 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260408_0012"
down_revision = "20260406_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_password_reset_tokens",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_password_reset_tokens_user_id"), "user_password_reset_tokens", ["user_id"], unique=False)
    op.create_index(
        op.f("ix_user_password_reset_tokens_token_hash"),
        "user_password_reset_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index(op.f("ix_user_password_reset_tokens_expires_at"), "user_password_reset_tokens", ["expires_at"], unique=False)
    op.create_index(op.f("ix_user_password_reset_tokens_used_at"), "user_password_reset_tokens", ["used_at"], unique=False)
    op.create_index(op.f("ix_user_password_reset_tokens_created_at"), "user_password_reset_tokens", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_password_reset_tokens_created_at"), table_name="user_password_reset_tokens")
    op.drop_index(op.f("ix_user_password_reset_tokens_used_at"), table_name="user_password_reset_tokens")
    op.drop_index(op.f("ix_user_password_reset_tokens_expires_at"), table_name="user_password_reset_tokens")
    op.drop_index(op.f("ix_user_password_reset_tokens_token_hash"), table_name="user_password_reset_tokens")
    op.drop_index(op.f("ix_user_password_reset_tokens_user_id"), table_name="user_password_reset_tokens")
    op.drop_table("user_password_reset_tokens")
