"""add action to login_logs

Revision ID: 621c123f4aa9
Revises: 302e0e07fbf6
Create Date: 2026-07-16 21:04:51.001907

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '621c123f4aa9'
down_revision: Union[str, None] = '302e0e07fbf6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('login_logs', sa.Column('action', sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column('login_logs', 'action')
