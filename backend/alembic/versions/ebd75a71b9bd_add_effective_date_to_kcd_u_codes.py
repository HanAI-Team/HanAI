"""add_effective_date_to_kcd_u_codes

Revision ID: ebd75a71b9bd
Revises: 86f341bb806a
Create Date: 2026-06-17 16:19:46.149745

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ebd75a71b9bd'
down_revision: Union[str, None] = '86f341bb806a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('kcd_u_codes', sa.Column('effective_date', sa.Date(), nullable=True))
    op.add_column('kcd_u_codes', sa.Column('expired_date', sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column('kcd_u_codes', 'expired_date')
    op.drop_column('kcd_u_codes', 'effective_date')
