"""add warn_notices to claim

Revision ID: e4732de84717
Revises: 5240951c5ad0
Create Date: 2026-07-10 13:42:20.372334

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4732de84717'
down_revision: Union[str, None] = '5240951c5ad0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('claims', sa.Column('warn_notices', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('claims', 'warn_notices')
