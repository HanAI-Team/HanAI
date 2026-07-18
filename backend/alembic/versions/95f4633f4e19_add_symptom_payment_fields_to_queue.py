"""add symptom payment fields to queue

Revision ID: 95f4633f4e19
Revises: 3dc82e8ac949
Create Date: 2026-07-18 14:02:23.243210

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '95f4633f4e19'
down_revision: Union[str, None] = '3dc82e8ac949'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('daily_queue', sa.Column('symptom', sa.String(500), nullable=True))
    op.add_column('daily_queue', sa.Column('queue_number', sa.Integer(), nullable=True))
    op.add_column('daily_queue', sa.Column('payment_method', sa.String(20), nullable=True))
    op.add_column('daily_queue', sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('daily_queue', 'paid_at')
    op.drop_column('daily_queue', 'payment_method')
    op.drop_column('daily_queue', 'queue_number')
    op.drop_column('daily_queue', 'symptom')
