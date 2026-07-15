"""add is_active to doctors

Revision ID: 302e0e07fbf6
Revises: ab0a06e477f2
Create Date: 2026-07-15 13:25:15.031079

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '302e0e07fbf6'
down_revision: Union[str, None] = 'ab0a06e477f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('doctors', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))


def downgrade() -> None:
    op.drop_column('doctors', 'is_active')
