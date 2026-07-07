"""update_fee_master_2026

Revision ID: i2j3k4l5m6n7
Revises: h1i2j3k4l5m6
Create Date: 2026-07-08 00:00:00.000000

h1i2j3k4l5m6 에서 잘못 추가된 AA/NA 코드 제거 후
40XXX HIRA 공식 코드를 2026-01-01 수가로 복원·갱신.
추나요법(40710/40720/40730)을 신규 추가.
"""
from typing import Sequence, Union
from alembic import op

revision: str = 'i2j3k4l5m6n7'
down_revision: Union[str, None] = 'h1i2j3k4l5m6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# h1i2j3k4l5m6 에서 잘못 삽입된 AA/NA 코드 (HIRA 한방 분류에 존재하지 않음)
_WRONG_CODES = (
    "AA159", "AA161", "AA163", "AA165", "AA167",
    "AA171", "AA173",
    "AA211", "AA213", "AA215",
    "NA161", "NA162",
)

# 복원 + 2026 수가 적용 대상 (h1i2j3k4l5m6 에서 삭제됐던 코드)
# (code, name, category, ih, im, iv, price)
_RESTORE_ROWS = [
    # 침술
    ("40011", "경혈침술(1부위)",       "침술",    True, True, True,  4070),
    ("40012", "경혈침술(2부위이상)",   "침술",    True, True, True,  6110),
    ("40030", "안와내침술",            "침술",    True, True, True,  4820),
    ("40040", "비강내침술",            "침술",    True, True, True,  4370),
    ("40050", "복강내침술",            "침술",    True, True, True,  4380),
    ("40060", "관절내침술",            "침술",    True, True, True,  4760),
    ("40070", "척추간침술",            "침술",    True, True, True,  4880),
    ("40080", "투자법침술",            "침술",    True, True, True,  4890),
    ("40091", "침전기자극술",           "전기/온열", True, True, False, 4180),
    ("40092", "전자침술",              "침술",    True, True, True,  4660),
    ("40100", "레이저침술",            "침술",    True, True, True,  4080),
    # 뜸
    ("40304", "구술(직접구-직접애주구)", "뜸",    True, True, True, 12280),
    ("40305", "구술(직접구-반흔구)",    "뜸",     True, True, True, 12310),
    ("40306", "구술(간접구-간접애주구)","뜸",     True, True, True,  5090),
    ("40307", "구술(간접구-기기구술)", "뜸",      True, True, True,  4370),
    # 부항
    ("40312", "부항술(자락관법)",       "부항",   True, True, True,  9830),
    ("40313", "부항술(자락관법-2부위이상)", "부항", True, True, True, 14740),
    ("40321", "부항술(건식-유관법)",    "부항",   True, True, True,  5590),
    ("40322", "부항술(건식-섬관법)",    "부항",   True, True, True,  6510),
    ("40323", "부항술(건식-주관법)",    "부항",   True, True, True,  6720),
]

# 신규 추나요법 코드 (2026 급여)
_CHUNA_ROWS = [
    ("40710", "추나요법(단순)",       "추나", True, True, False, 26330),
    ("40720", "추나요법(복잡)",       "추나", True, True, False, 44450),
    ("40721", "추나요법(복잡-80%)",   "추나", True, True, False, 44450),
    ("40730", "추나요법(특수-한구)",  "추나", True, True, False, 68140),
]

# 기존 유지 코드의 2026 수가 갱신
_PRICE_UPDATES = [
    # 진찰료
    ("10100", 15860),
    ("10200", 10010),
    ("11900",  7000),
    # 분구침술 (이미 DB에 있던 코드)
    ("40120",  4080),
    # 전기/온열
    ("40700",  2520),
    ("40701",  1940),
    ("40702",  2380),
    # 검사
    ("20010",  5340),
    ("20020",  5990),
    ("20030",  6870),
    ("20031",  5750),
    ("20032",  5430),
    ("29003",  5820),
    ("29004", 20530),
    ("29005", 36400),
    # 한약조제료
    ("30010",  1230),
    ("30020",  1400),
    ("30030",  1580),
    ("30040",  1760),
    ("30050",  1930),
    ("30070",  2290),
    ("30100",  2820),
    ("30140",  3530),
    ("30150",  3710),
    ("30160",  4490),
    ("30180",  5540),
    ("30190",  6440),
]

_EFFECTIVE = "2026-01-01"


def upgrade() -> None:
    # 1) 잘못된 AA/NA 코드 삭제
    wrong_sql = ", ".join(f"'{c}'" for c in _WRONG_CODES)
    op.execute(f"DELETE FROM fee_master WHERE code IN ({wrong_sql})")

    # 2) h1i2j3k4l5m6 에서 삭제됐던 40XXX 코드 복원 (2026 수가)
    for code, name, cat, ih, im, iv, price in _RESTORE_ROWS:
        op.execute(f"""
            INSERT INTO fee_master
                (code, name, category, insured_health, insured_medical_aid,
                 insured_veterans, unit_price, is_insured, effective_date)
            VALUES
                ('{code}', '{name}', '{cat}', {ih}, {im}, {iv},
                 {price}, true, '{_EFFECTIVE}')
            ON CONFLICT (code) DO UPDATE SET
                name           = EXCLUDED.name,
                category       = EXCLUDED.category,
                unit_price     = EXCLUDED.unit_price,
                effective_date = EXCLUDED.effective_date
        """)

    # 3) 추나요법 신규 삽입
    for code, name, cat, ih, im, iv, price in _CHUNA_ROWS:
        op.execute(f"""
            INSERT INTO fee_master
                (code, name, category, insured_health, insured_medical_aid,
                 insured_veterans, unit_price, is_insured, effective_date)
            VALUES
                ('{code}', '{name}', '{cat}', {ih}, {im}, {iv},
                 {price}, true, '{_EFFECTIVE}')
            ON CONFLICT (code) DO UPDATE SET
                name           = EXCLUDED.name,
                category       = EXCLUDED.category,
                unit_price     = EXCLUDED.unit_price,
                effective_date = EXCLUDED.effective_date
        """)

    # 4) 기존 코드 수가 갱신
    for code, price in _PRICE_UPDATES:
        op.execute(f"""
            UPDATE fee_master
            SET unit_price = {price}, effective_date = '{_EFFECTIVE}'
            WHERE code = '{code}'
        """)


def downgrade() -> None:
    # 추나/복원 코드 제거
    restored = [r[0] for r in _RESTORE_ROWS] + [r[0] for r in _CHUNA_ROWS]
    rm_sql = ", ".join(f"'{c}'" for c in restored)
    op.execute(f"DELETE FROM fee_master WHERE code IN ({rm_sql})")

    # AA/NA 코드 재삽입 (h1i2j3k4l5m6 상태로 롤백)
    for row in [
        ("AA159", "체침 단순침술",  "침술",  True,  True,  False, 6260),
        ("AA161", "전침",           "침술",  True,  True,  False, 8350),
        ("AA163", "도침(침도)",     "침술",  True,  True,  False, 12500),
        ("AA165", "화침",           "침술",  True,  True,  False, 9140),
        ("AA167", "수침(약침)",     "침술",  True,  True,  False, 10200),
        ("AA171", "뜸(단순)",       "뜸",    True,  True,  False, 4100),
        ("AA173", "뜸(복잡)",       "뜸",    True,  True,  False, 6150),
        ("AA211", "건부항(단순)",   "부항",  True,  True,  False, 3900),
        ("AA213", "건부항(복잡)",   "부항",  True,  True,  False, 5600),
        ("AA215", "습부항",         "부항",  True,  True,  False, 6700),
        ("NA161", "추나요법(경증)", "추나",  True,  True,  False, 20060),
        ("NA162", "추나요법(중증)", "추나",  True,  True,  False, 40120),
    ]:
        code, name, cat, ih, im, iv, price = row
        op.execute(f"""
            INSERT INTO fee_master
                (code, name, category, insured_health, insured_medical_aid,
                 insured_veterans, unit_price, is_insured, effective_date)
            VALUES
                ('{code}', '{name}', '{cat}', {ih}, {im}, {iv},
                 {price}, true, '2024-01-01')
            ON CONFLICT (code) DO NOTHING
        """)
