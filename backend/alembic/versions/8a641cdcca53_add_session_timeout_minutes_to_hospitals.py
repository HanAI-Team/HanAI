"""add session_timeout_minutes to hospitals

Revision ID: 8a641cdcca53
Revises: 130f692a8602
Create Date: 2026-07-23 16:36:05.170749

세션타임 재인증(HIRA 개인정보 접속기록 요건) 설정 기능 — 병원별 idle 타임아웃(분) 저장용
컬럼 추가. 5~30 범위는 앱 레이어(HospitalUpdate)에서 검증하며, 상한이 30분인 이유는
JWT_EXPIRE_MINUTES(30분)를 넘으면 idle 타이머가 돌기 전에 토큰이 먼저 만료되기 때문.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "8a641cdcca53"
down_revision: Union[str, None] = "130f692a8602"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "hospitals",
        sa.Column("session_timeout_minutes", sa.Integer(), server_default="30", nullable=True),
    )


def downgrade() -> None:
    op.drop_column("hospitals", "session_timeout_minutes")
