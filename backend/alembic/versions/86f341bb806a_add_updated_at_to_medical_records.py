"""add_updated_at_to_medical_records

Revision ID: 86f341bb806a
Revises: d998f487c79e
Create Date: 2026-06-17 16:17:31.637514

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '86f341bb806a'
down_revision: Union[str, None] = 'd998f487c79e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'medical_records',
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column('medical_records', 'updated_at')
