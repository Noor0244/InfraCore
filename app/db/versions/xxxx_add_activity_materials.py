from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'activity_materials',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('stretch_id', sa.Integer(), nullable=False),
        sa.Column('activity_id', sa.Integer(), nullable=False),
        sa.Column('project_material_id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('project_id', 'stretch_id', 'activity_id', 'project_material_id', name='uq_activity_material'),
    )

def downgrade():
    op.drop_table('activity_materials')
