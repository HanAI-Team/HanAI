"""add_kcd_sex_restriction_and_notifiable

Revision ID: b272c577f245
Revises: c2d3e4f5a6b7
Create Date: 2026-06-24 10:16:12.543617

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b272c577f245'
down_revision: Union[str, None] = 'c2d3e4f5a6b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('kcd_u_codes', sa.Column('sex_restriction', sa.String(1), nullable=True))
    op.add_column('kcd_u_codes', sa.Column('is_notifiable', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    op.drop_column('kcd_u_codes', 'is_notifiable')
    op.drop_column('kcd_u_codes', 'sex_restriction')
