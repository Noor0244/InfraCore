"""Add approval_status to daily_work_activities table

Revision ID: 20260214_02
Revises: 20260214_01
Create Date: 2026-02-14 15:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260214_02"
down_revision = "20260214_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "daily_work_activities",
        sa.Column(
            "approval_status",
            sa.String(length=20),
            nullable=True,
            server_default="Changed",
        ),
    )


def downgrade() -> None:
    op.drop_column("daily_work_activities", "approval_status")
