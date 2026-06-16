"""add_kcd_u_codes_table

Revision ID: f3c1a9e72b04
Revises: a5f5dec05aff
Create Date: 2026-06-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f3c1a9e72b04'
down_revision: Union[str, None] = 'a5f5dec05aff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'kcd_u_codes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('korean_name', sa.String(length=100), nullable=False),
        sa.Column('hanja', sa.String(length=100), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
    )
    op.create_index('ix_kcd_u_codes_code', 'kcd_u_codes', ['code'])


def downgrade() -> None:
    op.drop_index('ix_kcd_u_codes_code', table_name='kcd_u_codes')
    op.drop_table('kcd_u_codes')
