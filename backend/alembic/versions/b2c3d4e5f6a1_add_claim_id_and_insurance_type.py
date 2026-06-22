"""add_claim_id_to_medical_records_and_insurance_type_to_patients

Revision ID: b2c3d4e5f6a1
Revises: a1b2c3d4e5f6
Create Date: 2026-06-22 00:01:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = 'b2c3d4e5f6a1'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'medical_records',
        sa.Column('claim_id', UUID(as_uuid=True), sa.ForeignKey('claims.id'), nullable=True)
    )
    op.create_index('ix_medical_records_claim_id', 'medical_records', ['claim_id'])

    op.add_column(
        'patients',
        sa.Column('insurance_type', sa.String(), nullable=True, server_default='health')
    )


def downgrade() -> None:
    op.drop_column('patients', 'insurance_type')
    op.drop_index('ix_medical_records_claim_id', table_name='medical_records')
    op.drop_column('medical_records', 'claim_id')