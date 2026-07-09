"""widen kcd_u_codes korean_name column

Revision ID: f8eebf52fb78
Revises: b538a0b4b066
Create Date: 2026-07-09 09:22:41.766046

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f8eebf52fb78'
down_revision: Union[str, None] = 'b538a0b4b066'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("kcd_u_codes", "korean_name", type_=sa.String(150))


def downgrade() -> None:
    op.alter_column("kcd_u_codes", "korean_name", type_=sa.String(100))
