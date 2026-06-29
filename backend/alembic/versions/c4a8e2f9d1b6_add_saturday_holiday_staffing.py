"""add_saturday_holiday_staffing

Revision ID: c4a8e2f9d1b6
Revises: b0247c27c0b1
Create Date: 2026-06-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4a8e2f9d1b6'
down_revision: Union[str, None] = 'b0247c27c0b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'saturday_holiday_staffing',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('hospital_id', sa.UUID(), nullable=False),
        sa.Column('work_date', sa.Date(), nullable=False),
        sa.Column('doctor_count', sa.Numeric(3, 1), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('hospital_id', 'work_date', name='uq_sat_holiday_staffing_date'),
    )


def downgrade() -> None:
    op.drop_table('saturday_holiday_staffing')
