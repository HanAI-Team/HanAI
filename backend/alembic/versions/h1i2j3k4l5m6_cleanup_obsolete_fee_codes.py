"""cleanup_obsolete_fee_codes

Revision ID: h1i2j3k4l5m6
Revises: ec551044a67f
Create Date: 2026-07-08 00:00:00.000000

40XXX 구형 코드 제거 + AA/NA 코드 upsert.
마이그레이션 b3c4d5e6f7a8의 코드 체계(AA/NA)가 정식 HIRA 코드임을 확인 후 적용.
"""
from typing import Sequence, Union
from alembic import op

revision: str = 'h1i2j3k4l5m6'
down_revision: Union[str, None] = 'ec551044a67f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 제거 대상: AA/NA 코드로 대체되는 40XXX 구형 코드
_OBSOLETE_CODES = (
    # 침술 (→ AA159/AA161/AA163/AA165/AA167)
    "40011", "40012", "40030", "40040", "40050",
    "40060", "40070", "40080", "40091", "40092", "40100",
    # 뜸 (→ AA171/AA173)
    "40304", "40305", "40306", "40307",
    # 부항 (→ AA211/AA213/AA215)
    "40312", "40313", "40321", "40322", "40323",
    # 추나/도수 (→ NA161/NA162)
    "45550", "45560", "40400",
)

# 신규 추가 또는 단가 갱신 대상
_UPSERT_ROWS = [
    ("AA159", "체침 단순침술",  "침술",  True,  True,  False, 6260,  True,  "2024-01-01"),
    ("AA161", "전침",           "침술",  True,  True,  False, 8350,  True,  "2024-01-01"),
    ("AA163", "도침(침도)",     "침술",  True,  True,  False, 12500, True,  "2024-01-01"),
    ("AA165", "화침",           "침술",  True,  True,  False, 9140,  True,  "2024-01-01"),
    ("AA167", "수침(약침)",     "침술",  True,  True,  False, 10200, True,  "2024-01-01"),
    ("AA171", "뜸(단순)",       "뜸",    True,  True,  False, 4100,  True,  "2024-01-01"),
    ("AA173", "뜸(복잡)",       "뜸",    True,  True,  False, 6150,  True,  "2024-01-01"),
    ("AA211", "건부항(단순)",   "부항",  True,  True,  False, 3900,  True,  "2024-01-01"),
    ("AA213", "건부항(복잡)",   "부항",  True,  True,  False, 5600,  True,  "2024-01-01"),
    ("AA215", "습부항",         "부항",  True,  True,  False, 6700,  True,  "2024-01-01"),
    ("NA161", "추나요법(경증)", "추나",  True,  True,  False, 20060, True,  "2024-01-01"),
    ("NA162", "추나요법(중증)", "추나",  True,  True,  False, 40120, True,  "2024-01-01"),
]


def upgrade() -> None:
    codes_sql = ", ".join(f"'{c}'" for c in _OBSOLETE_CODES)
    op.execute(f"DELETE FROM fee_master WHERE code IN ({codes_sql})")

    for row in _UPSERT_ROWS:
        code, name, cat, ih, im, iv, price, insured, eff = row
        op.execute(f"""
            INSERT INTO fee_master (code, name, category, insured_health, insured_medical_aid, insured_veterans, unit_price, is_insured, effective_date)
            VALUES ('{code}', '{name}', '{cat}', {ih}, {im}, {iv}, {price}, {insured}, '{eff}')
            ON CONFLICT (code) DO UPDATE SET
                name = EXCLUDED.name,
                unit_price = EXCLUDED.unit_price,
                effective_date = EXCLUDED.effective_date
        """)


def downgrade() -> None:
    # 복구: 삭제된 40XXX 코드를 다시 삽입 (단가는 원래 값 기준)
    op.execute("""
        INSERT INTO fee_master (code, name, category, insured_health, insured_medical_aid, insured_veterans, unit_price, is_insured)
        VALUES
        ('40011','경혈침술(1부위)','침술',true,true,true,2620,true),
        ('40012','경혈침술(2부위이상)','침술',true,true,true,3920,true),
        ('40091','침전기자극술','전기/온열',true,true,false,3950,true),
        ('40304','구술(직접구-직접애주구)','뜸',true,true,true,5600,true),
        ('40305','구술(직접구-반흔구)','뜸',true,true,true,5840,true),
        ('40306','구술(간접구-간접애주구)','뜸',true,true,true,2320,true),
        ('40307','구술(간접구-기기구술)','뜸',true,true,true,2140,true),
        ('40312','부항술(자락관법)','부항',true,true,true,5570,true),
        ('40313','부항술(자락관법-2부위이상)','부항',true,true,true,8350,true),
        ('40321','부항술(건식-유관법)','부항',true,true,true,3470,true),
        ('40322','부항술(건식-섬관법)','부항',true,true,true,3720,true),
        ('40323','부항술(건식-주관법)','부항',true,true,true,4290,true),
        ('45550','총관도수법','추나/도수',true,true,false,4940,true),
        ('45560','첩대총관도수법','추나/도수',true,true,false,9370,true),
        ('40400','변증기술료','추나/도수',true,true,false,2500,true)
        ON CONFLICT (code) DO NOTHING
    """)
