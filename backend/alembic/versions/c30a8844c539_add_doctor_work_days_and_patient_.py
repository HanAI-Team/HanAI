"""add_doctor_work_days_and_patient_confirmation_no

Revision ID: c30a8844c539
Revises: e9f2c7a4b3d8
Create Date: 2026-07-03 13:37:24.116749

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c30a8844c539'
down_revision: Union[str, None] = 'e9f2c7a4b3d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('doctor_work_days',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('hospital_id', sa.UUID(), nullable=False),
    sa.Column('claim_period_year', sa.Integer(), nullable=False),
    sa.Column('claim_period_month', sa.Integer(), nullable=False),
    sa.Column('doctor_birth_date', sa.String(length=6), nullable=False),
    sa.Column('work_days', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('patients', sa.Column('confirmation_no', sa.String(length=13), nullable=True))


def downgrade() -> None:
    op.drop_column('patients', 'confirmation_no')
    op.drop_table('doctor_work_days')
