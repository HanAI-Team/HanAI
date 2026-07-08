"""merge_billing_and_ytk_chains

Revision ID: ec551044a67f
Revises: 49812262929f, g4b5c6d7e8f9
Create Date: 2026-07-07 12:24:35.327380

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ec551044a67f'
down_revision: Union[str, None] = ('49812262929f', 'g4b5c6d7e8f9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
