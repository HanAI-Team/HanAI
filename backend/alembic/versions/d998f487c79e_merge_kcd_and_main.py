"""merge_kcd_and_main

Revision ID: d998f487c79e
Revises: 2638682e756b, f3c1a9e72b04
Create Date: 2026-06-17 16:17:26.753598

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd998f487c79e'
down_revision: Union[str, None] = ('2638682e756b', 'f3c1a9e72b04')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
