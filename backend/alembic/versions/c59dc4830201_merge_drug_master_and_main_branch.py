"""merge drug_master and main branch

Revision ID: c59dc4830201
Revises: 8c1774fee41d, d46f8556a759
Create Date: 2026-07-10 13:20:20.054553

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c59dc4830201'
down_revision: Union[str, None] = ('8c1774fee41d', 'd46f8556a759')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
