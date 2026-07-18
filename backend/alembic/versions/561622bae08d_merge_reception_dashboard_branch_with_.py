"""merge reception-dashboard branch with is_active/access-control-log branch

Revision ID: 561622bae08d
Revises: 8fbcf6b41389, ed0550148c0b
Create Date: 2026-07-18 20:58:52.889963

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '561622bae08d'
down_revision: Union[str, None] = ('8fbcf6b41389', 'ed0550148c0b')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
