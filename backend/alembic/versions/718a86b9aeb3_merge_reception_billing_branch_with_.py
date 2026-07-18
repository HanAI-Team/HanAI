"""merge reception-billing branch with queue symptom/payment fields branch

Revision ID: 718a86b9aeb3
Revises: 561622bae08d, 95f4633f4e19
Create Date: 2026-07-19 03:40:22.954931

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '718a86b9aeb3'
down_revision: Union[str, None] = ('561622bae08d', '95f4633f4e19')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
