"""add_claims_table

Revision ID: a1b2c3d4e5f6
Revises: 7d6bca2d417b
Create Date: 2026-06-22 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '7d6bca2d417b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'claims',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('patient_id', UUID(as_uuid=True), sa.ForeignKey('patients.id'), nullable=False),
        sa.Column('doctor_id', UUID(as_uuid=True), sa.ForeignKey('doctors.id'), nullable=False),
        sa.Column('hospital_id', UUID(as_uuid=True), sa.ForeignKey('hospitals.id'), nullable=False),
        sa.Column('claim_period_year', sa.Integer(), nullable=False),
        sa.Column('claim_period_month', sa.Integer(), nullable=False),
        sa.Column('claim_type', sa.String(), nullable=True),
        sa.Column('total_amount', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('patient_copay', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('claim_amount', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('differential_index', sa.Numeric(5, 2), nullable=True, server_default='1.0'),
        sa.Column('status', sa.String(), nullable=False, server_default='draft'),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_claims_patient_id', 'claims', ['patient_id'])
    op.create_index('ix_claims_hospital_id', 'claims', ['hospital_id'])
    op.create_index('ix_claims_period', 'claims', ['claim_period_year', 'claim_period_month'])


def downgrade() -> None:
    op.drop_index('ix_claims_period', table_name='claims')
    op.drop_index('ix_claims_hospital_id', table_name='claims')
    op.drop_index('ix_claims_patient_id', table_name='claims')
    op.drop_table('claims')