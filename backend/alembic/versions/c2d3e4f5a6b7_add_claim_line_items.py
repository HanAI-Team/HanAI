"""add_claim_line_items

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-06-24 00:00:00.000000

차트 화면에서 항목 클릭 시 생성되는 ClaimLineItem 테이블 추가.
EDI C2-71 명세서진료내역과 1:1 대응.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'c2d3e4f5a6b7'
down_revision: Union[str, None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'claim_line_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('claim_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('medical_record_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hang', sa.String(2), nullable=False),
        sa.Column('mok', sa.String(2), nullable=False),
        sa.Column('code', sa.String(9), nullable=False),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('unit_price', sa.Numeric(10, 2), nullable=False, server_default='0'),
        sa.Column('qty', sa.Numeric(5, 2), nullable=False, server_default='1'),
        sa.Column('days', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('amount', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('hyeolmyeong_names', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['claim_id'], ['claims.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['medical_record_id'], ['medical_records.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('claim_line_items')
