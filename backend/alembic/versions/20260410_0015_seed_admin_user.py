"""seed default admin user (dev bootstrap; change password in production)

Revision ID: 20260410_0015
Revises: 20260410_0014
Create Date: 2026-04-10 00:00:00
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision = "20260410_0015"
down_revision = "20260410_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    row = conn.execute(sa.text("SELECT id FROM users WHERE username = :u"), {"u": "admin"}).fetchone()
    if row is not None:
        return

    from app.services.password_identity_provider import PasswordIdentityProvider

    user_id = str(uuid4())
    password_hash = PasswordIdentityProvider._hash_password("admin")
    now = datetime.now(timezone.utc)
    conn.execute(
        sa.text(
            """
            INSERT INTO users (id, username, email, email_verified_at, password_hash, created_at)
            VALUES (:id, :username, :email, :email_verified_at, :password_hash, :created_at)
            """
        ),
        {
            "id": user_id,
            "username": "admin",
            "email": "admin@localhost.local",
            "email_verified_at": now,
            "password_hash": password_hash,
            "created_at": now,
        },
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM users WHERE username = 'admin' AND email = 'admin@localhost.local'"))
