"""add_special_case_needs_review_to_claims

Revision ID: 49812262929f
Revises: a3d7e2c9f6b1
Create Date: 2026-07-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '49812262929f'
down_revision: Union[str, None] = 'a3d7e2c9f6b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('claims', sa.Column('special_case_needs_review', sa.Boolean(), server_default='false', nullable=False))


def downgrade() -> None:
    op.drop_column('claims', 'special_case_needs_review')
