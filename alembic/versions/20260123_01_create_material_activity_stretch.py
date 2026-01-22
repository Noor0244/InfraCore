
"""
create material_activity and material_stretch tables
"""
from alembic import op
import sqlalchemy as sa

# Alembic identifiers
revision = '20260123_01_create_material_activity_stretch'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'material_activities',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('material_id', sa.Integer(), sa.ForeignKey('materials.id'), nullable=False, index=True),
        sa.Column('activity_id', sa.Integer(), sa.ForeignKey('activities.id'), nullable=False, index=True),
        sa.UniqueConstraint('material_id', 'activity_id', name='uq_material_activity'),
    )
    op.create_table(
        'material_stretches',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('material_id', sa.Integer(), sa.ForeignKey('materials.id'), nullable=False, index=True),
        sa.Column('stretch_id', sa.Integer(), sa.ForeignKey('road_stretches.id'), nullable=False, index=True),
        sa.UniqueConstraint('material_id', 'stretch_id', name='uq_material_stretch'),
    )

def downgrade():
    op.drop_table('material_stretches')
    op.drop_table('material_activities')
