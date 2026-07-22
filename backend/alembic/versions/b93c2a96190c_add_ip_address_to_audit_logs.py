"""add ip_address to audit_logs

Revision ID: b93c2a96190c
Revises: ffe21842956a
Create Date: 2026-07-23 08:06:55.042027

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b93c2a96190c'
down_revision: Union[str, None] = 'ffe21842956a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('audit_logs', sa.Column('ip_address', sa.String(length=45), nullable=True))


def downgrade() -> None:
    op.drop_column('audit_logs', 'ip_address')
