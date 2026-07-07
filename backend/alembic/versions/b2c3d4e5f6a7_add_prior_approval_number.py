"""add_prior_approval_number_to_special_case_registrations

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-07 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('special_case_registrations',
        sa.Column('prior_approval_number', sa.String(30), nullable=True))


def downgrade() -> None:
    op.drop_column('special_case_registrations', 'prior_approval_number')
