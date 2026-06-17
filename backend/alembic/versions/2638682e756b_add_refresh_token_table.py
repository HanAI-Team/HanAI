"""add_refresh_token_table

Revision ID: 2638682e756b
Revises: c1d2e3f4a5b6
Create Date: 2026-06-01 00:00:00.000000

NOTE: stub 파일 — refresh_token 테이블은 DB에 이미 존재하나 파일이 삭제됨.
upgrade/downgrade는 no-op.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '2638682e756b'
down_revision: Union[str, None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
