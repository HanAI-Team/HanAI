"""add_special_case_registrations

Revision ID: a3d7e2c9f6b1
Revises: f4b9c1a7d3e2
Create Date: 2026-07-06 00:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3d7e2c9f6b1'
down_revision: Union[str, None] = 'f4b9c1a7d3e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'special_case_registrations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('patient_id', sa.UUID(), nullable=False),
        sa.Column('special_code', sa.String(length=4), nullable=False),
        sa.Column('category', sa.String(length=20), nullable=False),
        sa.Column('registered_disease_code', sa.String(length=10), nullable=True),
        sa.Column('registered_at', sa.Date(), nullable=False),
        sa.Column('expires_at', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=10), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('special_case_registrations')
