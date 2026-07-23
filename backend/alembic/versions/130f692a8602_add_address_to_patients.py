"""add address to patients

Revision ID: 130f692a8602
Revises: b93c2a96190c
Create Date: 2026-07-23 12:27:30.874214

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '130f692a8602'
down_revision: Union[str, None] = 'b93c2a96190c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('patients', sa.Column('address', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('patients', 'address')
