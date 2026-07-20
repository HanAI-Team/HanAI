"""add_billing_agent_to_claims

Revision ID: n7o8p9q0r1s2
Revises: m6n7o8p9q0r1
Create Date: 2026-07-20 00:00:00.000000

대행청구단체 입력 기능 — 청구건별 대행청구단체 코드/명 저장용 컬럼 추가.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "n7o8p9q0r1s2"
down_revision: Union[str, None] = "m6n7o8p9q0r1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("claims", sa.Column("billing_agent_code", sa.String(length=5), nullable=True))
    op.add_column("claims", sa.Column("billing_agent_name", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("claims", "billing_agent_name")
    op.drop_column("claims", "billing_agent_code")
