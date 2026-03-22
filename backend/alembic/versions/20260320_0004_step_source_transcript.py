"""Persist exact source transcript provenance on process steps.

Revision ID: 20260320_0004
Revises: 20260320_0003
Create Date: 2026-03-20 17:25:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260320_0004"
down_revision = "20260320_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("process_steps", sa.Column("source_transcript_artifact_id", sa.String(length=36), nullable=True))
    op.create_index(
        "ix_process_steps_source_transcript_artifact_id",
        "process_steps",
        ["source_transcript_artifact_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_process_steps_source_transcript_artifact_id", table_name="process_steps")
    op.drop_column("process_steps", "source_transcript_artifact_id")
