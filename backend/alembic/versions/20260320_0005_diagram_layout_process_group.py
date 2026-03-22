"""Add process-group scoping to diagram layouts.

Revision ID: 20260320_0005
Revises: 20260320_0004
Create Date: 2026-03-20 18:20:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260320_0005"
down_revision = "20260320_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("diagram_layouts", sa.Column("process_group_id", sa.String(length=36), nullable=True))
    op.create_index("ix_diagram_layouts_process_group_id", "diagram_layouts", ["process_group_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_diagram_layouts_process_group_id", table_name="diagram_layouts")
    op.drop_column("diagram_layouts", "process_group_id")
