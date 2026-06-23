"""add_edi_columns_to_procedures

Revision ID: f1a2b3c4d5e6
Revises: a1b2c3d4e5f6
Create Date: 2026-06-23 00:00:00.000000

EDI 명세서진료내역 생성에 필요한 컬럼 추가.
기존 details JSON이 아닌 명시적 컬럼으로 관리해 쿼리와 검증이 용이하도록 함.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('medical_record_procedures', sa.Column('hang',           sa.String(2),         nullable=True))
    op.add_column('medical_record_procedures', sa.Column('mok',            sa.String(2),         nullable=True))
    op.add_column('medical_record_procedures', sa.Column('code_gubun',     sa.String(1),         nullable=True, server_default='A'))
    op.add_column('medical_record_procedures', sa.Column('unit_price',     sa.Numeric(12, 2),    nullable=True))
    op.add_column('medical_record_procedures', sa.Column('qty',            sa.Numeric(7, 2),     nullable=True))
    op.add_column('medical_record_procedures', sa.Column('days',           sa.Integer(),         nullable=True))
    op.add_column('medical_record_procedures', sa.Column('license_type',   sa.String(1),         nullable=True, server_default='3'))
    op.add_column('medical_record_procedures', sa.Column('license_no',     sa.String(10),        nullable=True))
    op.add_column('medical_record_procedures', sa.Column('special_detail', sa.String(700),       nullable=True))


def downgrade() -> None:
    for col in ('special_detail', 'license_no', 'license_type', 'days', 'qty', 'unit_price', 'code_gubun', 'mok', 'hang'):
        op.drop_column('medical_record_procedures', col)
