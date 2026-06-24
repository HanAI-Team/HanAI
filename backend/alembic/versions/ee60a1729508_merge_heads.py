"""merge_heads

Revision ID: ee60a1729508
Revises: 8d67c792fba9, b1c2d3e4f5a6
Create Date: 2026-06-24 15:21:06.939173

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ee60a1729508'
down_revision: Union[str, None] = ('8d67c792fba9', 'b1c2d3e4f5a6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
