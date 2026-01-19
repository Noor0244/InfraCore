"""
Alembic migration for SSR master tables: ssr_project_types, ssr_units, ssr_chapters, ssr_items
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'ssr_project_types',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('code', sa.String(length=32), nullable=False, unique=True),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.String(length=256)),
        sa.Column('is_active', sa.Boolean(), default=True)
    )
    op.create_table(
        'ssr_units',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('symbol', sa.String(length=16), nullable=False, unique=True),
        sa.Column('description', sa.String(length=128))
    )
    op.create_table(
        'ssr_chapters',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('project_type_id', sa.Integer(), sa.ForeignKey('ssr_project_types.id'), nullable=False),
        sa.Column('chapter_code', sa.String(length=32), nullable=False),
        sa.Column('chapter_name', sa.String(length=128), nullable=False),
        sa.Column('display_order', sa.Integer(), default=0)
    )
    op.create_table(
        'ssr_items',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('project_type_id', sa.Integer(), sa.ForeignKey('ssr_project_types.id'), nullable=False),
        sa.Column('chapter_id', sa.Integer(), sa.ForeignKey('ssr_chapters.id'), nullable=False),
        sa.Column('item_code', sa.String(length=64), nullable=False),
        sa.Column('item_description', sa.Text(), nullable=False),
        sa.Column('unit_id', sa.Integer(), sa.ForeignKey('ssr_units.id'), nullable=False),
        sa.Column('rate', sa.Numeric(12, 2)),
        sa.Column('is_active', sa.Boolean(), default=True)
    )

def downgrade():
    op.drop_table('ssr_items')
    op.drop_table('ssr_chapters')
    op.drop_table('ssr_units')
    op.drop_table('ssr_project_types')
