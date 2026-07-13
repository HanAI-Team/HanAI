"""add agency_code to hospitals

Revision ID: 37fb632f500f
Revises: 9ebbcdc0822b
Create Date: 2026-07-13 12:56:44.314434

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '37fb632f500f'
down_revision: Union[str, None] = '9ebbcdc0822b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('hospitals', sa.Column('agency_code', sa.String(5), nullable=True))


def downgrade() -> None:
    op.drop_column('hospitals', 'agency_code')
