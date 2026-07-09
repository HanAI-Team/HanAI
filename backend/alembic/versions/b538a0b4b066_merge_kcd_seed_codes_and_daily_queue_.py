"""merge kcd seed codes and daily queue heads

Revision ID: b538a0b4b066
Revises: 91061a283822, k4l5m6n7o8p9
Create Date: 2026-07-09 09:20:39.441731

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b538a0b4b066'
down_revision: Union[str, None] = ('91061a283822', 'k4l5m6n7o8p9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
