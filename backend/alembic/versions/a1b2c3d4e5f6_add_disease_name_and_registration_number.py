"""add_disease_name_and_registration_number_to_special_case_registrations

Revision ID: a1b2c3d4e5f6
Revises: f4b9c1a7d3e2
Create Date: 2026-07-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f4b9c1a7d3e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('special_case_registrations',
        sa.Column('disease_name', sa.String(100), nullable=True))
    op.add_column('special_case_registrations',
        sa.Column('registration_number', sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column('special_case_registrations', 'registration_number')
    op.drop_column('special_case_registrations', 'disease_name')
