"""add_doctor_birth_date

Revision ID: 5300360feb6b
Revises: c30a8844c539
Create Date: 2026-07-06 00:03:29.640513

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5300360feb6b'
down_revision: Union[str, None] = 'c30a8844c539'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('doctors', sa.Column('birth_date', sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column('doctors', 'birth_date')
