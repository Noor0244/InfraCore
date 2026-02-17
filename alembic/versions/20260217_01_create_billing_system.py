"""Create billing system tables

Revision ID: 20260217_01_create_billing_system
Revises: 20260214_02_add_approval_status_to_daily_work_activities
Create Date: 2026-02-17 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260217_01_create_billing_system'
down_revision = '20260214_02_add_approval_status_to_daily_work_activities'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create material_rates table
    op.create_table(
        'material_rates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('material_id', sa.Integer(), nullable=False),
        sa.Column('vendor_id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('unit_price', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(10), nullable=False, server_default='INR'),
        sa.Column('gst_percentage', sa.Float(), nullable=False, server_default='18.0'),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('delivery_charges', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('handling_charges', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('notes', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['material_id'], ['materials.id'], ),
        sa.ForeignKeyConstraint(['vendor_id'], ['material_vendors.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_material_rates_material_id'), 'material_rates', ['material_id'], unique=False)
    op.create_index(op.f('ix_material_rates_vendor_id'), 'material_rates', ['vendor_id'], unique=False)
    op.create_index(op.f('ix_material_rates_project_id'), 'material_rates', ['project_id'], unique=False)

    # Create bills table
    op.create_table(
        'bills',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('bill_number', sa.String(50), nullable=False, unique=True),
        sa.Column('bill_date', sa.Date(), nullable=False),
        sa.Column('vendor_id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('payment_terms', sa.String(100), nullable=True),
        sa.Column('subtotal', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('gst_amount', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('delivery_charges', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('other_charges', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('discount_amount', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('total_amount', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('paid_amount', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('payment_status', sa.String(50), nullable=False, server_default='PENDING'),
        sa.Column('currency', sa.String(10), nullable=False, server_default='INR'),
        sa.Column('bill_type', sa.String(50), nullable=False, server_default='MATERIAL'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('reference_number', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['vendor_id'], ['material_vendors.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bills_bill_number'), 'bills', ['bill_number'], unique=False)
    op.create_index(op.f('ix_bills_bill_date'), 'bills', ['bill_date'], unique=False)
    op.create_index(op.f('ix_bills_vendor_id'), 'bills', ['vendor_id'], unique=False)
    op.create_index(op.f('ix_bills_project_id'), 'bills', ['project_id'], unique=False)

    # Create bill_items table
    op.create_table(
        'bill_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('bill_id', sa.Integer(), nullable=False),
        sa.Column('material_id', sa.Integer(), nullable=False),
        sa.Column('procurement_log_id', sa.Integer(), nullable=True),
        sa.Column('description', sa.String(300), nullable=True),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(50), nullable=False),
        sa.Column('unit_price', sa.Float(), nullable=False),
        sa.Column('line_total', sa.Float(), nullable=False),
        sa.Column('gst_percentage', sa.Float(), nullable=False, server_default='18.0'),
        sa.Column('gst_amount', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('line_total_with_gst', sa.Float(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['bill_id'], ['bills.id'], ),
        sa.ForeignKeyConstraint(['material_id'], ['materials.id'], ),
        sa.ForeignKeyConstraint(['procurement_log_id'], ['procurement_logs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_bill_items_bill_id'), 'bill_items', ['bill_id'], unique=False)
    op.create_index(op.f('ix_bill_items_material_id'), 'bill_items', ['material_id'], unique=False)
    op.create_index(op.f('ix_bill_items_procurement_log_id'), 'bill_items', ['procurement_log_id'], unique=False)

    # Create payments table
    op.create_table(
        'payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('payment_number', sa.String(50), nullable=False, unique=True),
        sa.Column('payment_date', sa.Date(), nullable=False),
        sa.Column('bill_id', sa.Integer(), nullable=False),
        sa.Column('vendor_id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('amount_paid', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(10), nullable=False, server_default='INR'),
        sa.Column('payment_method', sa.String(50), nullable=False),
        sa.Column('cheque_number', sa.String(50), nullable=True),
        sa.Column('bank_name', sa.String(100), nullable=True),
        sa.Column('transaction_reference', sa.String(100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_reconciled', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['bill_id'], ['bills.id'], ),
        sa.ForeignKeyConstraint(['vendor_id'], ['material_vendors.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payments_payment_number'), 'payments', ['payment_number'], unique=False)
    op.create_index(op.f('ix_payments_payment_date'), 'payments', ['payment_date'], unique=False)
    op.create_index(op.f('ix_payments_bill_id'), 'payments', ['bill_id'], unique=False)


def downgrade() -> None:
    op.drop_table('payments')
    op.drop_table('bill_items')
    op.drop_table('bills')
    op.drop_table('material_rates')
