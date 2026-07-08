"""add daily_queue table

Revision ID: 91061a283822
Revises: bc5472195d72
Create Date: 2026-07-08 19:07:29.881982

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '91061a283822'
down_revision: Union[str, None] = 'bc5472195d72'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('daily_queue',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('hospital_id', sa.UUID(), nullable=False),
    sa.Column('patient_id', sa.UUID(), nullable=False),
    sa.Column('doctor_id', sa.UUID(), nullable=True),
    sa.Column('queue_date', sa.Date(), nullable=False),
    sa.Column('checked_in_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('source', sa.String(length=20), nullable=False),
    sa.ForeignKeyConstraint(['doctor_id'], ['doctors.id'], ),
    sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id'], ),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('daily_queue')
