"""merge agency_code branch and acupoint branch

Revision ID: ab0a06e477f2
Revises: 5ef0afd54549, 9ebbcdc0822b
Create Date: 2026-07-13 13:02:28.368547

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ab0a06e477f2'
down_revision: Union[str, None] = ('5ef0afd54549', '9ebbcdc0822b')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
