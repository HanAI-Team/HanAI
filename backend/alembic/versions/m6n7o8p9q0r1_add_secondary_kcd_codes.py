"""add_secondary_kcd_codes

Revision ID: m6n7o8p9q0r1
Revises: l5m6n7o8p9q0
Create Date: 2026-07-20 00:00:00.000000

착오청구 예방(상병 묶음 자동생성 방지) — 부상병 코드 목록 저장용 컬럼 추가.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "m6n7o8p9q0r1"
down_revision: Union[str, None] = "l5m6n7o8p9q0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "medical_records",
        sa.Column("secondary_kcd_codes", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("medical_records", "secondary_kcd_codes")
