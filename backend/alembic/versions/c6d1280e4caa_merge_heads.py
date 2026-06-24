"""merge_heads

Revision ID: c6d1280e4caa
Revises: 3d20d6824663, b1c2d3e4f5a6
Create Date: 2026-06-24 10:14:52.486742

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c6d1280e4caa'
down_revision: Union[str, None] = ('3d20d6824663', 'b1c2d3e4f5a6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
