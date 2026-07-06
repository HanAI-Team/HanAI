"""add disability_grade, disability_medical_aid, support_fund, is_non_benefit

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-07-07 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f3a4b5c6d7e8'
down_revision: Union[str, None] = 'e2f3a4b5c6d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Patient: 장애 등급 (의료급여 장애인 본인부담 경감 산정 기준)
    op.add_column('patients',
        sa.Column('disability_grade', sa.String(1), nullable=True))

    # Claim: C2-11 명세서일반내역 장애인의료비·지원금·비급여총액
    op.add_column('claims',
        sa.Column('disability_medical_aid', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('claims',
        sa.Column('support_fund', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('claims',
        sa.Column('non_benefit_total', sa.Integer(), nullable=False, server_default='0'))

    # MedicalRecordProcedure: 비급여 여부 (True이면 non_benefit_total에 합산)
    op.add_column('medical_record_procedures',
        sa.Column('is_non_benefit', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    op.drop_column('medical_record_procedures', 'is_non_benefit')
    op.drop_column('claims', 'non_benefit_total')
    op.drop_column('claims', 'support_fund')
    op.drop_column('claims', 'disability_medical_aid')
    op.drop_column('patients', 'disability_grade')
