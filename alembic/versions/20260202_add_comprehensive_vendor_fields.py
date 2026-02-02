"""Add comprehensive vendor fields to material_vendors table

Revision ID: 20260202_01
Revises: 20260123_01_create_material_activity_stretch
Create Date: 2026-02-02 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260202_01'
down_revision = '20260123_01_create_material_activity_stretch'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to material_vendors table
    op.add_column('material_vendors', sa.Column('vendor_type', sa.String(100), nullable=True))
    op.add_column('material_vendors', sa.Column('vendor_location', sa.String(200), nullable=True))
    op.add_column('material_vendors', sa.Column('service_area', sa.String(300), nullable=True))
    op.add_column('material_vendors', sa.Column('vendor_priority', sa.String(50), nullable=True, server_default='Primary'))
    op.add_column('material_vendors', sa.Column('reliability_rating', sa.String(50), nullable=True, server_default='Medium'))
    op.add_column('material_vendors', sa.Column('payment_terms', sa.String(100), nullable=True))
    op.add_column('material_vendors', sa.Column('credit_period', sa.Integer(), nullable=True))
    op.add_column('material_vendors', sa.Column('gst_number', sa.String(50), nullable=True))
    op.add_column('material_vendors', sa.Column('gst_percentage', sa.Float(), nullable=True, server_default='18.0'))
    op.add_column('material_vendors', sa.Column('unit_price', sa.Float(), nullable=True))
    op.add_column('material_vendors', sa.Column('per_unit_quantity', sa.Float(), nullable=True))
    op.add_column('material_vendors', sa.Column('supply_capacity', sa.Float(), nullable=True))
    op.add_column('material_vendors', sa.Column('contract_start_date', sa.DateTime(), nullable=True))
    op.add_column('material_vendors', sa.Column('contract_end_date', sa.DateTime(), nullable=True))
    op.add_column('material_vendors', sa.Column('quotation_pdf', sa.String(500), nullable=True))
    op.add_column('material_vendors', sa.Column('agreement_pdf', sa.String(500), nullable=True))
    op.add_column('material_vendors', sa.Column('gst_certificate', sa.String(500), nullable=True))


def downgrade() -> None:
    # Remove columns in reverse order
    op.drop_column('material_vendors', 'gst_certificate')
    op.drop_column('material_vendors', 'agreement_pdf')
    op.drop_column('material_vendors', 'quotation_pdf')
    op.drop_column('material_vendors', 'contract_end_date')
    op.drop_column('material_vendors', 'contract_start_date')
    op.drop_column('material_vendors', 'supply_capacity')
    op.drop_column('material_vendors', 'per_unit_quantity')
    op.drop_column('material_vendors', 'unit_price')
    op.drop_column('material_vendors', 'gst_percentage')
    op.drop_column('material_vendors', 'gst_number')
    op.drop_column('material_vendors', 'credit_period')
    op.drop_column('material_vendors', 'payment_terms')
    op.drop_column('material_vendors', 'reliability_rating')
    op.drop_column('material_vendors', 'vendor_priority')
    op.drop_column('material_vendors', 'service_area')
    op.drop_column('material_vendors', 'vendor_location')
    op.drop_column('material_vendors', 'vendor_type')
