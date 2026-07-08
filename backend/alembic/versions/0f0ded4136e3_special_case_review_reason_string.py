"""special_case review_reason string

Revision ID: 0f0ded4136e3
Revises: b4c5d6e7f8a9
Create Date: 2026-07-07 21:10:36.113925

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0f0ded4136e3'
down_revision: Union[str, None] = 'b4c5d6e7f8a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('claims', sa.Column('special_case_review_reason', sa.String(length=100), nullable=True))
    op.drop_column('claims', 'special_case_needs_review')


def downgrade() -> None:
    op.add_column('claims', sa.Column('special_case_needs_review', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False))
    op.drop_column('claims', 'special_case_review_reason')
