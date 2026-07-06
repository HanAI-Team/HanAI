"""add_doctor_id_to_doctor_work_days

Revision ID: f4b9c1a7d3e2
Revises: 5300360feb6b
Create Date: 2026-07-06 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4b9c1a7d3e2'
down_revision: Union[str, None] = '5300360feb6b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('doctor_work_days', sa.Column('doctor_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_doctor_work_days_doctor_id', 'doctor_work_days', 'doctors', ['doctor_id'], ['id']
    )
    op.create_unique_constraint(
        'uq_doctor_work_days_period_doctor',
        'doctor_work_days',
        ['hospital_id', 'claim_period_year', 'claim_period_month', 'doctor_id'],
    )


def downgrade() -> None:
    op.drop_constraint('uq_doctor_work_days_period_doctor', 'doctor_work_days', type_='unique')
    op.drop_constraint('fk_doctor_work_days_doctor_id', 'doctor_work_days', type_='foreignkey')
    op.drop_column('doctor_work_days', 'doctor_id')
