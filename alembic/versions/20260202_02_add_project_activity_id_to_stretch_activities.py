"""Add project_activity_id to stretch_activities table

Revision ID: 20260202_02
Revises: 20260202_01
Create Date: 2026-02-02 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260202_02'
down_revision = '20260202_01'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add project_activity_id column to stretch_activities table
    op.add_column('stretch_activities', sa.Column('project_activity_id', sa.Integer(), nullable=True, index=True))
    op.create_foreign_key('fk_stretch_activities_project_activity_id', 'stretch_activities', 'project_activities', ['project_activity_id'], ['id'])


def downgrade() -> None:
    # Remove foreign key and column
    op.drop_constraint('fk_stretch_activities_project_activity_id', 'stretch_activities', type_='foreignkey')
    op.drop_column('stretch_activities', 'project_activity_id')
