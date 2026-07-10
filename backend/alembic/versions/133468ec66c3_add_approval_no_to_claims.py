"""add approval_no to claims

Revision ID: 133468ec66c3
Revises: 8c1774fee41d
Create Date: 2026-07-10 14:40:55.446169

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '133468ec66c3'
down_revision: Union[str, None] = '8c1774fee41d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('claims', sa.Column('approval_no', sa.String(length=35), nullable=True))


def downgrade() -> None:
    op.drop_column('claims', 'approval_no')
