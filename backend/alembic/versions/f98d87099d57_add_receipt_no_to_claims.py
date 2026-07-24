"""add receipt_no to claims

Revision ID: f98d87099d57
Revises: 8a641cdcca53
Create Date: 2026-07-24 16:19:21.482664

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f98d87099d57'
down_revision: Union[str, None] = '8a641cdcca53'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('claims', sa.Column('receipt_no', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('claims', 'receipt_no')
