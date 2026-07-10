"""add data_purge_logs table

Revision ID: 4d73318a33f8
Revises: e4732de84717
Create Date: 2026-07-10 14:13:07.712794

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '4d73318a33f8'
down_revision: Union[str, None] = 'e4732de84717'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'data_purge_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('doctor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('patient_name_before', sa.String(), nullable=True),
        sa.Column('reason', sa.String(), nullable=False),
        sa.Column('purge_type', sa.String(), nullable=False, server_default='anonymize'),
        sa.Column('purged_at', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id']),
        sa.ForeignKeyConstraint(['doctor_id'], ['doctors.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('data_purge_logs')
