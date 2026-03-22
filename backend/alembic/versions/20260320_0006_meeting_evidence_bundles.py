"""Add meeting evidence bundles and artifact upload pairing fields.

Revision ID: 20260320_0006
Revises: 20260320_0005
Create Date: 2026-03-20 20:15:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260320_0006"
down_revision = "20260320_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("artifacts", sa.Column("upload_batch_id", sa.String(length=36), nullable=True))
    op.add_column("artifacts", sa.Column("upload_pair_index", sa.Integer(), nullable=True))
    op.create_index("ix_artifacts_upload_batch_id", "artifacts", ["upload_batch_id"], unique=False)

    op.create_table(
        "meeting_evidence_bundles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("meeting_id", sa.String(length=36), nullable=False),
        sa.Column("upload_batch_id", sa.String(length=36), nullable=False),
        sa.Column("pair_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("transcript_artifact_id", sa.String(length=36), nullable=True),
        sa.Column("video_artifact_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["draft_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["transcript_artifact_id"], ["artifacts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["video_artifact_id"], ["artifacts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_meeting_evidence_bundles_session_id", "meeting_evidence_bundles", ["session_id"], unique=False)
    op.create_index("ix_meeting_evidence_bundles_meeting_id", "meeting_evidence_bundles", ["meeting_id"], unique=False)
    op.create_index(
        "ix_meeting_evidence_bundles_upload_batch_id",
        "meeting_evidence_bundles",
        ["upload_batch_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_meeting_evidence_bundles_upload_batch_id", table_name="meeting_evidence_bundles")
    op.drop_index("ix_meeting_evidence_bundles_meeting_id", table_name="meeting_evidence_bundles")
    op.drop_index("ix_meeting_evidence_bundles_session_id", table_name="meeting_evidence_bundles")
    op.drop_table("meeting_evidence_bundles")

    op.drop_index("ix_artifacts_upload_batch_id", table_name="artifacts")
    op.drop_column("artifacts", "upload_pair_index")
    op.drop_column("artifacts", "upload_batch_id")
