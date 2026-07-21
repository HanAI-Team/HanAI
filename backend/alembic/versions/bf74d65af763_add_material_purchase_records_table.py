"""add material_purchase_records table

Revision ID: bf74d65af763
Revises: 4bb673fcdbc4
Create Date: 2026-07-21 10:14:58.111459

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'bf74d65af763'
down_revision: Union[str, None] = '4bb673fcdbc4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'material_purchase_records',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('hospital_id', sa.UUID(), nullable=False),
        sa.Column('record_type', sa.String(length=20), nullable=False),
        sa.Column('item_name', sa.String(length=200), nullable=False),
        sa.Column('item_code', sa.String(length=20), nullable=True),
        sa.Column('spec', sa.String(length=100), nullable=True),
        sa.Column('quantity', sa.Numeric(precision=10, scale=2), server_default='1', nullable=False),
        sa.Column('unit_price', sa.Integer(), server_default='0', nullable=False),
        sa.Column('amount', sa.Integer(), server_default='0', nullable=False),
        sa.Column('supplier_name', sa.String(length=100), nullable=True),
        sa.Column('transaction_date', sa.Date(), nullable=False),
        sa.Column('reported', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('reported_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('material_purchase_records')
