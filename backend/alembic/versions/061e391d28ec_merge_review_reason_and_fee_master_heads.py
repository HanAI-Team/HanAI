"""merge review_reason and fee_master heads

Revision ID: 061e391d28ec
Revises: 0f0ded4136e3, i2j3k4l5m6n7
Create Date: 2026-07-08 16:41:39.924830

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '061e391d28ec'
down_revision: Union[str, None] = ('0f0ded4136e3', 'i2j3k4l5m6n7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
