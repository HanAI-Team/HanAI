"""add_fee_master_table

Revision ID: a1b2c3d4e5f6
Revises: 7d6bca2d417b
Create Date: 2026-06-23 00:00:00.000000

한방 행위코드 수가 마스터 테이블.
수가는 2024년 HIRA 요양급여비용 목록표 기준(원 단위).
실제 청구 전 심평원 최신 고시 확인 필요.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '7d6bca2d417b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'fee_master',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('category', sa.String(length=20), nullable=False),
        sa.Column('insurance_types', sa.String(length=10), nullable=False, server_default='4'),
        sa.Column('unit_price', sa.Integer(), nullable=False),
        sa.Column('is_insured', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('effective_date', sa.Date(), nullable=True),
        sa.Column('expired_date', sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
    )
    op.create_index('ix_fee_master_code', 'fee_master', ['code'])

    # 초기 데이터: 한방 주요 행위코드 (2024 HIRA 수가 기준)
    op.execute("""
        INSERT INTO fee_master (code, name, category, insurance_types, unit_price, is_insured, effective_date) VALUES
        -- 침술
        ('AA159', '체침 단순침술', '침술', '4,5,7', 6260, true, '2024-01-01'),
        ('AA161', '전침', '침술', '4,5,7', 8350, true, '2024-01-01'),
        ('AA163', '도침(침도)', '침술', '4,5,7', 12500, true, '2024-01-01'),
        ('AA165', '화침', '침술', '4,5,7', 9140, true, '2024-01-01'),
        ('AA167', '수침(약침)', '침술', '4,5,7', 10200, true, '2024-01-01'),
        -- 뜸
        ('AA171', '뜸(단순)', '뜸', '4,5,7', 4100, true, '2024-01-01'),
        ('AA173', '뜸(복잡)', '뜸', '4,5,7', 6150, true, '2024-01-01'),
        -- 부항
        ('AA211', '건부항(단순)', '부항', '4,5,7', 3900, true, '2024-01-01'),
        ('AA213', '건부항(복잡)', '부항', '4,5,7', 5600, true, '2024-01-01'),
        ('AA215', '습부항', '부항', '4,5,7', 6700, true, '2024-01-01'),
        -- 추나
        ('NA161', '추나요법(경증)', '추나', '4,5', 20060, true, '2024-01-01'),
        ('NA162', '추나요법(중증)', '추나', '4,5', 40120, true, '2024-01-01')
    """)


def downgrade() -> None:
    op.drop_index('ix_fee_master_code', table_name='fee_master')
    op.drop_table('fee_master')
