"""add_medical_record_procedures_and_acupuncture_forbidden

Revision ID: d4e5f6a1b2c3
Revises: c3d4e5f6a1b2
Create Date: 2026-06-22 00:03:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = 'd4e5f6a1b2c3'
down_revision: Union[str, None] = 'c3d4e5f6a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'medical_record_procedures',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('medical_record_id', UUID(as_uuid=True), sa.ForeignKey('medical_records.id', ondelete='CASCADE'), nullable=False),
        sa.Column('procedure_type', sa.String(), nullable=False),
        sa.Column('procedure_code', sa.String(), nullable=True),
        sa.Column('details', JSONB, nullable=True),
        sa.Column('amount', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_procedures_medical_record_id', 'medical_record_procedures', ['medical_record_id'])
    op.create_index('ix_procedures_type', 'medical_record_procedures', ['procedure_type'])

    op.add_column(
        'acupuncture_points',
        sa.Column('forbidden_with', JSONB, nullable=True)
    )


def downgrade() -> None:
    op.drop_column('acupuncture_points', 'forbidden_with')
    op.drop_index('ix_procedures_type', table_name='medical_record_procedures')
    op.drop_index('ix_procedures_medical_record_id', table_name='medical_record_procedures')
    op.drop_table('medical_record_procedures')