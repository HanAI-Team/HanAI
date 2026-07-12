"""경혈-진료내역 FK 연결: claim_line_item_acupoints 테이블 추가

Revision ID: 9ebbcdc0822b
Revises: 4d73318a33f8
Create Date: 2026-07-12 00:00:00.000000

"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '9ebbcdc0822b'
down_revision: Union[str, None] = '4d73318a33f8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "claim_line_item_acupoints",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "claim_line_item_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("claim_line_items.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "acupuncture_point_code", sa.String(10),
            sa.ForeignKey("acupuncture_points.code"), nullable=False,
        ),
        sa.Column("korean_name", sa.String(50), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "claim_line_item_id", "acupuncture_point_code", name="uq_line_item_acupoint",
        ),
    )
    op.create_index(
        "ix_claim_line_item_acupoints_line_item_id",
        "claim_line_item_acupoints", ["claim_line_item_id"],
    )

    # 기존 hyeolmyeong_names(JSON 이름 리스트) → 코드 매칭 best-effort 이관.
    # 완전일치로 정확히 1개 후보만 있으면 이관, 모호/미존재는 건너뛰고 로그로 남긴다.
    conn = op.get_bind()
    all_points = conn.execute(sa.text("SELECT code, korean_name FROM acupuncture_points")).fetchall()
    name_to_codes: dict[str, list[str]] = {}
    for code, korean_name in all_points:
        name_to_codes.setdefault(korean_name, []).append(code)

    rows = conn.execute(sa.text(
        "SELECT id, hyeolmyeong_names FROM claim_line_items WHERE hyeolmyeong_names IS NOT NULL"
    )).fetchall()

    skipped: list[tuple] = []
    for line_item_id, names in rows:
        if not names:
            continue
        for order, name in enumerate(names):
            candidates = name_to_codes.get(name, [])
            if len(candidates) != 1:
                skipped.append((line_item_id, name, len(candidates)))
                continue
            conn.execute(sa.text(
                "INSERT INTO claim_line_item_acupoints "
                "(claim_line_item_id, acupuncture_point_code, korean_name, display_order) "
                "VALUES (:lid, :code, :name, :ord) "
                "ON CONFLICT (claim_line_item_id, acupuncture_point_code) DO NOTHING"
            ), {"lid": line_item_id, "code": candidates[0], "name": name, "ord": order})

    if skipped:
        print(f"[claim_line_item_acupoints migration] 매칭 실패/모호 {len(skipped)}건 건너뜀:")
        for lid, name, count in skipped[:50]:
            reason = "미존재" if count == 0 else f"모호({count}개 후보)"
            print(f"  - line_item_id={lid}, name={name!r}: {reason}")


def downgrade() -> None:
    op.drop_index("ix_claim_line_item_acupoints_line_item_id", table_name="claim_line_item_acupoints")
    op.drop_table("claim_line_item_acupoints")
