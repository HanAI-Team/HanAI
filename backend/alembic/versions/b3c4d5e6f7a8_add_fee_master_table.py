"""add_fee_master_table

Revision ID: b3c4d5e6f7a8
Revises: e5f6a1b2c3d4
Create Date: 2026-06-23 00:00:00.000000

한방 행위코드 수가 마스터 테이블.
수가는 2024년 HIRA 요양급여비용 목록표 기준(원 단위).
실제 청구 전 심평원 최신 고시 확인 필요.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b3c4d5e6f7a8'
down_revision: Union[str, None] = 'e5f6a1b2c3d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'fee_master',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('category', sa.String(length=20), nullable=False),
        sa.Column('insured_health', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('insured_medical_aid', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('insured_veterans', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('unit_price', sa.Integer(), nullable=False),
        sa.Column('is_insured', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('effective_date', sa.Date(), nullable=True),
        sa.Column('expired_date', sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
    )
    op.create_index('ix_fee_master_code', 'fee_master', ['code'])

    # 초기 데이터: 한방 주요 행위코드 (2024 HIRA 수가 기준)
    # insured_health=건강보험(4), insured_medical_aid=의료급여(5), insured_veterans=보훈(7)
    op.execute("""
        INSERT INTO fee_master (code, name, category, insured_health, insured_medical_aid, insured_veterans, unit_price, is_insured, effective_date) VALUES
        -- 침술 (건강보험·의료급여·보훈 모두 적용)
        ('AA159', '체침 단순침술', '침술', true, true, true, 6260, true, '2024-01-01'),
        ('AA161', '전침',         '침술', true, true, true, 8350, true, '2024-01-01'),
        ('AA163', '도침(침도)',   '침술', true, true, true, 12500, true, '2024-01-01'),
        ('AA165', '화침',         '침술', true, true, true, 9140, true, '2024-01-01'),
        ('AA167', '수침(약침)',   '침술', true, true, true, 10200, true, '2024-01-01'),
        -- 뜸 (건강보험·의료급여·보훈 모두 적용)
        ('AA171', '뜸(단순)', '뜸', true, true, true, 4100, true, '2024-01-01'),
        ('AA173', '뜸(복잡)', '뜸', true, true, true, 6150, true, '2024-01-01'),
        -- 부항 (건강보험·의료급여·보훈 모두 적용)
        ('AA211', '건부항(단순)', '부항', true, true, true, 3900, true, '2024-01-01'),
        ('AA213', '건부항(복잡)', '부항', true, true, true, 5600, true, '2024-01-01'),
        ('AA215', '습부항',       '부항', true, true, true, 6700, true, '2024-01-01'),
        -- 추나 (건강보험·의료급여만 적용, 보훈 제외)
        ('NA161', '추나요법(경증)', '추나', true, true, false, 20060, true, '2024-01-01'),
        ('NA162', '추나요법(중증)', '추나', true, true, false, 40120, true, '2024-01-01')
    """)


def downgrade() -> None:
    op.drop_index('ix_fee_master_code', table_name='fee_master')
    op.drop_table('fee_master')
