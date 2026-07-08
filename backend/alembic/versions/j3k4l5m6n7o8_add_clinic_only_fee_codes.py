"""add_clinic_only_fee_codes

Revision ID: j3k4l5m6n7o8
Revises: i2j3k4l5m6n7
Create Date: 2026-07-08 00:00:00.000000

의원 전용 코드 추가:
  154A6 — 소아과이외 6세미만 소아료 (한방의원 진찰료 가산)
  30200 — 한약의약품 조제복약지도료
  40400 — 번증기제료
단가는 2026-07-01 HIRA 고시 기준 (미확인 항목은 별도 표시).
"""
from typing import Sequence, Union

from alembic import op

revision: str = "j3k4l5m6n7o8"
down_revision: Union[str, None] = "i2j3k4l5m6n7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ROWS = [
    # (code, name, category, insured_health, insured_medical_aid, insured_veterans, unit_price)
    ("154A6", "소아과이외 6세미만 소아료",      "진찰료", True,  True,  False, 2640),
    ("30200", "한약의약품 조제복약지도료",        "한약",   True,  True,  False, 4200),
    ("40400", "번증기제료",                       "기타",   True,  True,  False, 2640),
]

_EFF = "2026-07-01"


def upgrade() -> None:
    for code, name, cat, ih, im, iv, price in _ROWS:
        op.execute(f"""
            INSERT INTO fee_master
                (code, name, category, insured_health, insured_medical_aid,
                 insured_veterans, unit_price, is_insured, effective_date)
            VALUES
                ('{code}', '{name}', '{cat}', {ih}, {im}, {iv},
                 {price}, true, '{_EFF}')
            ON CONFLICT (code) DO UPDATE SET
                name           = EXCLUDED.name,
                category       = EXCLUDED.category,
                unit_price     = EXCLUDED.unit_price,
                effective_date = EXCLUDED.effective_date
        """)


def downgrade() -> None:
    codes = ", ".join(f"'{r[0]}'" for r in _ROWS)
    op.execute(f"DELETE FROM fee_master WHERE code IN ({codes})")
