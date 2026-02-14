"""Add quantity to activity_materials table

Revision ID: 20260214_01
Revises: 20260213_01
Create Date: 2026-02-14 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260214_01'
down_revision = '20260213_01'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('activity_materials', sa.Column('quantity', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('activity_materials', 'quantity')
