"""add_billing_columns_to_prescriptions

Revision ID: c3d4e5f6a1b2
Revises: b2c3d4e5f6a1
Create Date: 2026-06-22 00:02:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'c3d4e5f6a1b2'
down_revision: Union[str, None] = 'b2c3d4e5f6a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('prescriptions', sa.Column('prescription_type', sa.String(), nullable=True))
    op.add_column('prescriptions', sa.Column('adjustment_type', sa.String(), nullable=True))
    op.add_column('prescriptions', sa.Column('formula_code', sa.String(), nullable=True))
    op.add_column('prescriptions', sa.Column('unit_price', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('prescriptions', sa.Column('daily_dosage_ratio', sa.Numeric(4, 2), nullable=True, server_default='1.0'))
    op.add_column('prescriptions', sa.Column('total_dosage_days', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('prescriptions', sa.Column('total_dosage_price', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('prescriptions', sa.Column('species_count', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('prescriptions', sa.Column('total_weight_g', sa.Numeric(8, 2), nullable=True, server_default='0'))
    op.add_column('prescriptions', sa.Column('low_cost_substitute', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('prescriptions', sa.Column('low_cost_surcharge', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('prescriptions', sa.Column('dispensing_fee', sa.Integer(), nullable=True, server_default='0'))


def downgrade() -> None:
    for col in [
        'prescription_type', 'adjustment_type', 'formula_code',
        'unit_price', 'daily_dosage_ratio', 'total_dosage_days', 'total_dosage_price',
        'species_count', 'total_weight_g',
        'low_cost_substitute', 'low_cost_surcharge', 'dispensing_fee',
    ]:
        op.drop_column('prescriptions', col)