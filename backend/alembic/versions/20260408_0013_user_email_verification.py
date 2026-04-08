"""user email + email verification tokens

Revision ID: 20260408_0013
Revises: 20260408_0012
Create Date: 2026-04-08 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260408_0013"
down_revision = "20260408_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "user_email_verification_tokens",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_user_email_verification_tokens_user_id"),
        "user_email_verification_tokens",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_email_verification_tokens_token_hash"),
        "user_email_verification_tokens",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        op.f("ix_user_email_verification_tokens_expires_at"),
        "user_email_verification_tokens",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_user_email_verification_tokens_expires_at"), table_name="user_email_verification_tokens")
    op.drop_index(op.f("ix_user_email_verification_tokens_token_hash"), table_name="user_email_verification_tokens")
    op.drop_index(op.f("ix_user_email_verification_tokens_user_id"), table_name="user_email_verification_tokens")
    op.drop_table("user_email_verification_tokens")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_column("users", "email_verified_at")
    op.drop_column("users", "email")
