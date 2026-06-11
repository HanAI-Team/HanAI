"""add_selected_result_to_medical_records

Revision ID: 94cd73bd4fa2
Revises: 92fbb6626669
Create Date: 2026-06-12 07:33:33.388145

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '94cd73bd4fa2'
down_revision: Union[str, None] = '92fbb6626669'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('medical_records', sa.Column('selected_result', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('medical_records', 'selected_result')
