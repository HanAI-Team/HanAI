"""merge_heads

Revision ID: e5f6a1b2c3d4
Revises: 7d6bca2d417b, d4e5f6a1b2c3
Create Date: 2026-06-22 00:04:00.000000
"""
from typing import Sequence, Union

revision: str = 'e5f6a1b2c3d4'
down_revision: Union[str, Sequence[str], None] = ('7d6bca2d417b', 'd4e5f6a1b2c3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass