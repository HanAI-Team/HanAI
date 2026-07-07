"""
한의원 청구 가능 항목 — 심평원 요양급여비용 목록표 2026-01-01 기준.

코드 체계: 40XXX 숫자 코드 (HIRA 공식 한방 행위코드)
  - 40011~40120: 침술
  - 40304~40307: 뜸(구술)
  - 40312~40323: 부항술
  - 40710~40730: 추나요법 (2024 급여 편입, 2026 수가)
  - 40091, 40700~40702: 전기/온열

hang/mok: HIRA EDI 명세 항번호/목번호
  - 01/01: 진찰료
  - 04/01: 시술처치 > 침술
  - 04/02: 시술처치 > 구술(뜸)
  - 04/03: 시술처치 > 부항
  - 04/04: 시술처치 > 전기/온열
  - 04/05: 시술처치 > 추나
  - 05/01: 검사
  - 11/01: 한약조제
  - 09/01: 비급여

단가 기준: 한방병원단가 (hanbang_fee_master_20260701.csv, 적용일 2026-01-01)
"""

from dataclasses import dataclass


@dataclass
class BillableItemDef:
    id: str
    name: str
    sub: str
    category: str
    hang: str
    mok: str
    code: str
    unit_price: float
    is_insured: bool = True
    requires_hyeolmyeong: bool = False


# 추나 코드 집합 — 본인부담률 50% 별도 적용 대상
CHUNA_CODES: frozenset[str] = frozenset({"40710", "40720", "40721", "40730"})


BILLABLE_CATALOG: list[BillableItemDef] = [
    # ── 진찰료 ──────────────────────────────────────────────────
    BillableItemDef(
        id="visit_initial", name="초진진찰료", sub="",
        category="진찰료", hang="01", mok="01",
        code="10100", unit_price=15860,
    ),
    BillableItemDef(
        id="visit_revisit", name="재진진찰료", sub="",
        category="진찰료", hang="01", mok="01",
        code="10200", unit_price=10010,
    ),
    BillableItemDef(
        id="visit_consult", name="협의진찰료", sub="한방병원",
        category="진찰료", hang="01", mok="01",
        code="11900", unit_price=7000,
    ),

    # ── 침술 (40XXX, 2026 수가) ──────────────────────────────────
    BillableItemDef(
        id="acu_1", name="경혈침술(1부위)", sub="",
        category="침술", hang="04", mok="01",
        code="40011", unit_price=4070,
        requires_hyeolmyeong=True,
    ),
    BillableItemDef(
        id="acu_2p", name="경혈침술(2부위이상)", sub="",
        category="침술", hang="04", mok="01",
        code="40012", unit_price=6110,
        requires_hyeolmyeong=True,
    ),
    BillableItemDef(
        id="acu_orbital", name="안와내침술", sub="",
        category="침술", hang="04", mok="01",
        code="40030", unit_price=4820,
    ),
    BillableItemDef(
        id="acu_nasal", name="비강내침술", sub="",
        category="침술", hang="04", mok="01",
        code="40040", unit_price=4370,
    ),
    BillableItemDef(
        id="acu_abdom", name="복강내침술", sub="",
        category="침술", hang="04", mok="01",
        code="40050", unit_price=4380,
    ),
    BillableItemDef(
        id="acu_joint", name="관절내침술", sub="",
        category="침술", hang="04", mok="01",
        code="40060", unit_price=4760,
    ),
    BillableItemDef(
        id="acu_spine", name="척추간침술", sub="",
        category="침술", hang="04", mok="01",
        code="40070", unit_price=4880,
    ),
    BillableItemDef(
        id="acu_embed", name="투자법침술", sub="",
        category="침술", hang="04", mok="01",
        code="40080", unit_price=4890,
    ),
    BillableItemDef(
        id="acu_electro", name="전자침술", sub="",
        category="침술", hang="04", mok="01",
        code="40092", unit_price=4660,
    ),
    BillableItemDef(
        id="acu_laser", name="레이저침술", sub="",
        category="침술", hang="04", mok="01",
        code="40100", unit_price=4080,
    ),
    BillableItemDef(
        id="acu_bun", name="분구침술", sub="이침/두침/족침 등",
        category="침술", hang="04", mok="01",
        code="40120", unit_price=4080,
    ),

    # ── 뜸 (구술, 2026 수가) ────────────────────────────────────
    BillableItemDef(
        id="mox_dir_ae", name="구술(직접구-직접애주구)", sub="",
        category="뜸", hang="04", mok="02",
        code="40304", unit_price=12280,
    ),
    BillableItemDef(
        id="mox_dir_scar", name="구술(직접구-반흔구)", sub="",
        category="뜸", hang="04", mok="02",
        code="40305", unit_price=12310,
    ),
    BillableItemDef(
        id="mox_ind_ae", name="구술(간접구-간접애주구)", sub="",
        category="뜸", hang="04", mok="02",
        code="40306", unit_price=5090,
    ),
    BillableItemDef(
        id="mox_ind_dev", name="구술(간접구-기기구술)", sub="",
        category="뜸", hang="04", mok="02",
        code="40307", unit_price=4370,
    ),

    # ── 부항술 (2026 수가) ───────────────────────────────────────
    BillableItemDef(
        id="cup_wet", name="부항술(자락관법)", sub="",
        category="부항", hang="04", mok="03",
        code="40312", unit_price=9830,
    ),
    BillableItemDef(
        id="cup_wet_2p", name="부항술(자락관법-2부위이상)", sub="",
        category="부항", hang="04", mok="03",
        code="40313", unit_price=14740,
    ),
    BillableItemDef(
        id="cup_dry_u", name="부항술(건식-유관법)", sub="",
        category="부항", hang="04", mok="03",
        code="40321", unit_price=5590,
    ),
    BillableItemDef(
        id="cup_dry_s", name="부항술(건식-섬관법)", sub="",
        category="부항", hang="04", mok="03",
        code="40322", unit_price=6510,
    ),
    BillableItemDef(
        id="cup_dry_j", name="부항술(건식-주관법)", sub="",
        category="부항", hang="04", mok="03",
        code="40323", unit_price=6720,
    ),

    # ── 전기/온열 (2026 수가) ────────────────────────────────────
    BillableItemDef(
        id="elec_stim", name="침전기자극술", sub="",
        category="전기/온열", hang="04", mok="04",
        code="40091", unit_price=4180,
    ),
    BillableItemDef(
        id="heat_warm", name="온냉경락요법(온열)", sub="경피경근온열요법",
        category="전기/온열", hang="04", mok="04",
        code="40700", unit_price=2520,
    ),
    BillableItemDef(
        id="heat_ir", name="온냉경락요법(적외선)", sub="경피적외선조사요법",
        category="전기/온열", hang="04", mok="04",
        code="40701", unit_price=1940,
    ),
    BillableItemDef(
        id="heat_cold", name="온냉경락요법(한냉)", sub="경피경근한냉요법",
        category="전기/온열", hang="04", mok="04",
        code="40702", unit_price=2380,
    ),

    # ── 추나요법 (2026 수가, 급여 적용) ─────────────────────────
    BillableItemDef(
        id="chuna_simple", name="추나요법(단순)", sub="",
        category="추나", hang="04", mok="05",
        code="40710", unit_price=26330,
    ),
    BillableItemDef(
        id="chuna_complex", name="추나요법(복잡)", sub="",
        category="추나", hang="04", mok="05",
        code="40720", unit_price=44450,
    ),
    BillableItemDef(
        id="chuna_special", name="추나요법(특수-한구)", sub="",
        category="추나", hang="04", mok="05",
        code="40730", unit_price=68140,
    ),

    # ── 검사 (2026 수가) ────────────────────────────────────────
    BillableItemDef(
        id="test_yang", name="양도락검사", sub="",
        category="검사", hang="05", mok="01",
        code="20010", unit_price=5340,
    ),
    BillableItemDef(
        id="test_pulse", name="맥전도검사", sub="",
        category="검사", hang="05", mok="01",
        code="20020", unit_price=5990,
    ),
    BillableItemDef(
        id="test_gyeong", name="경락기능검사", sub="",
        category="검사", hang="05", mok="01",
        code="20030", unit_price=6870,
    ),
    BillableItemDef(
        id="test_gyeong_y", name="경락기능검사(양명경)", sub="",
        category="검사", hang="05", mok="01",
        code="20031", unit_price=5750,
    ),
    BillableItemDef(
        id="test_gyeong_s", name="경락기능검사(수양명경)", sub="",
        category="검사", hang="05", mok="01",
        code="20032", unit_price=5430,
    ),
    BillableItemDef(
        id="test_vertigo", name="현훈검사", sub="",
        category="검사", hang="05", mok="01",
        code="29003", unit_price=5820,
    ),
    BillableItemDef(
        id="test_person", name="인성검사", sub="",
        category="검사", hang="05", mok="01",
        code="29004", unit_price=20530,
    ),
    BillableItemDef(
        id="test_dementia", name="치매검사", sub="",
        category="검사", hang="05", mok="01",
        code="29005", unit_price=36400,
    ),

    # ── 한약조제료 (2026 수가) ───────────────────────────────────
    BillableItemDef(
        id="herb_01", name="한약조제료(1일분)", sub="",
        category="한약", hang="11", mok="01",
        code="30010", unit_price=1230,
    ),
    BillableItemDef(
        id="herb_02", name="한약조제료(2일분)", sub="",
        category="한약", hang="11", mok="01",
        code="30020", unit_price=1400,
    ),
    BillableItemDef(
        id="herb_03", name="한약조제료(3일분)", sub="",
        category="한약", hang="11", mok="01",
        code="30030", unit_price=1580,
    ),
    BillableItemDef(
        id="herb_04", name="한약조제료(4일분)", sub="",
        category="한약", hang="11", mok="01",
        code="30040", unit_price=1760,
    ),
    BillableItemDef(
        id="herb_05", name="한약조제료(5일분)", sub="",
        category="한약", hang="11", mok="01",
        code="30050", unit_price=1930,
    ),
    BillableItemDef(
        id="herb_07", name="한약조제료(7일분)", sub="",
        category="한약", hang="11", mok="01",
        code="30070", unit_price=2290,
    ),
    BillableItemDef(
        id="herb_10", name="한약조제료(10일분)", sub="",
        category="한약", hang="11", mok="01",
        code="30100", unit_price=2820,
    ),
    BillableItemDef(
        id="herb_14", name="한약조제료(14일분)", sub="",
        category="한약", hang="11", mok="01",
        code="30140", unit_price=3530,
    ),
    BillableItemDef(
        id="herb_15", name="한약조제료(15일분)", sub="",
        category="한약", hang="11", mok="01",
        code="30150", unit_price=3710,
    ),
    BillableItemDef(
        id="herb_30", name="한약조제료(16~30일분)", sub="",
        category="한약", hang="11", mok="01",
        code="30160", unit_price=4490,
    ),
    BillableItemDef(
        id="herb_60", name="한약조제료(31~60일분)", sub="",
        category="한약", hang="11", mok="01",
        code="30180", unit_price=5540,
    ),
    BillableItemDef(
        id="herb_61p", name="한약조제료(61일분이상)", sub="",
        category="한약", hang="11", mok="01",
        code="30190", unit_price=6440,
    ),

    # ── 비급여 ──────────────────────────────────────────────────
    BillableItemDef(
        id="yakchim", name="약침술", sub="단가 자율책정",
        category="비급여", hang="09", mok="01",
        code="49010", unit_price=0,
        is_insured=False,
    ),
]


def get_catalog_item(item_id: str) -> BillableItemDef:
    for item in BILLABLE_CATALOG:
        if item.id == item_id:
            return item
    raise ValueError(f"정의되지 않은 항목: {item_id}")
