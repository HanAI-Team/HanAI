"""add_institution_code_and_patient_rrn

Revision ID: a9b8c7d6e5f4
Revises: f1a2b3c4d5e6
Create Date: 2026-06-23 00:00:00.000000

Hospital.institution_code: 심평원 요양기관기호 (8자리)
Patient.rrn: 주민등록번호 (AES-256-GCM 암호화 저장, 환경변수 RRN_ENCRYPTION_KEY 필요)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a9b8c7d6e5f4'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('hospitals', sa.Column('institution_code', sa.String(8), nullable=True))
    op.add_column('patients', sa.Column('rrn', sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column('patients', 'rrn')
    op.drop_column('hospitals', 'institution_code')
