"""drop refresh_token table

Revision ID: 5240951c5ad0
Revises: c59dc4830201
Create Date: 2026-07-10 13:34:28.596008

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5240951c5ad0'
down_revision: Union[str, None] = 'c59dc4830201'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS refresh_token")


def downgrade() -> None:
    op.create_table(
        'refresh_token',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
