"""Add unit to material_activities table

Revision ID: 20260213_01
Revises: 20260202_02
Create Date: 2026-02-13 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260213_01'
down_revision = '20260202_02'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('material_activities', sa.Column('unit', sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column('material_activities', 'unit')
