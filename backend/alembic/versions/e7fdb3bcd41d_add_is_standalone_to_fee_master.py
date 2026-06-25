"""add_is_standalone_to_fee_master

Revision ID: e7fdb3bcd41d
Revises: b272c577f245
Create Date: 2026-06-24 11:07:10.150455

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e7fdb3bcd41d'
down_revision: Union[str, None] = 'b272c577f245'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('fee_master', sa.Column('is_standalone', sa.Boolean(), server_default='false', nullable=False))


def downgrade() -> None:
    op.drop_column('fee_master', 'is_standalone')
