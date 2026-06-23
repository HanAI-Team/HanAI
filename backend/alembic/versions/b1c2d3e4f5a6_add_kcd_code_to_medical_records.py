"""add_kcd_code_to_medical_records

Revision ID: b1c2d3e4f5a6
Revises: a9b8c7d6e5f4
Create Date: 2026-06-23 00:00:00.000000

MedicalRecord.kcd_code: EDI C2-02 상병내역에 사용할 KCD 상병코드
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, None] = 'a9b8c7d6e5f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('medical_records', sa.Column('kcd_code', sa.String(10), nullable=True))


def downgrade() -> None:
    op.drop_column('medical_records', 'kcd_code')
