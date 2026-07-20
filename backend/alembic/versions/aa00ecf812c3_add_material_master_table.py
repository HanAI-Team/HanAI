"""add material_master table

Revision ID: aa00ecf812c3
Revises: 718a86b9aeb3
Create Date: 2026-07-20 09:53:26.345862

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'aa00ecf812c3'
down_revision: Union[str, None] = '718a86b9aeb3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'material_master',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('unit_price', sa.Integer(), nullable=False),
        sa.Column('effective_date', sa.Date(), nullable=True),
        sa.Column('expired_date', sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_material_master_code'), 'material_master', ['code'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_material_master_code'), table_name='material_master')
    op.drop_table('material_master')
