"""
한의원 청구 가능 항목 — 심평원 고시 기준 실수가 데이터.

hang/mok: HIRA EDI 명세 항번호/목번호
  - 01/01: 진찰료
  - 04/01: 시술처치 > 침술
  - 04/02: 시술처치 > 구술(뜸)
  - 04/03: 시술처치 > 부항
  - 04/04: 시술처치 > 전기/온열
  - 04/05: 시술처치 > 추나/도수
  - 05/01: 검사
  - 11/01: 한약조제
  - 09/01: 비급여
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


BILLABLE_CATALOG: list[BillableItemDef] = [
    # ── 진찰료 ──────────────────────────────────────────────────
    BillableItemDef(
        id="visit_initial", name="초진진찰료", sub="",
        category="진찰료", hang="01", mok="01",
        code="10100", unit_price=11560,
    ),
    BillableItemDef(
        id="visit_revisit", name="재진진찰료", sub="",
        category="진찰료", hang="01", mok="01",
        code="10200", unit_price=7290,
    ),
    BillableItemDef(
        id="visit_consult", name="협의진찰료", sub="한의원",
        category="진찰료", hang="01", mok="01",
        code="11900", unit_price=5100,
    ),

    # ── 침술 ────────────────────────────────────────────────────
    BillableItemDef(
        id="acu_1", name="경혈침술(1부위)", sub="",
        category="침술", hang="04", mok="01",
        code="40011", unit_price=2620,
        requires_hyeolmyeong=True,
    ),
    BillableItemDef(
        id="acu_2", name="경혈침술(2부위이상)", sub="",
        category="침술", hang="04", mok="01",
        code="40012", unit_price=3920,
        requires_hyeolmyeong=True,
    ),
    BillableItemDef(
        id="acu_orbital", name="안와내침술", sub="",
        category="침술", hang="04", mok="01",
        code="40030", unit_price=2880,
    ),
    BillableItemDef(
        id="acu_nasal", name="비강내침술", sub="",
        category="침술", hang="04", mok="01",
        code="40040", unit_price=2880,
    ),
    BillableItemDef(
        id="acu_abd", name="복강내침술", sub="",
        category="침술", hang="04", mok="01",
        code="40050", unit_price=2860,
    ),
    BillableItemDef(
        id="acu_joint", name="관절내침술", sub="",
        category="침술", hang="04", mok="01",
        code="40060", unit_price=2720,
    ),
    BillableItemDef(
        id="acu_spinal", name="척추간침술", sub="",
        category="침술", hang="04", mok="01",
        code="40070", unit_price=2840,
    ),
    BillableItemDef(
        id="acu_trans", name="투자법침술", sub="",
        category="침술", hang="04", mok="01",
        code="40080", unit_price=4220,
    ),
    BillableItemDef(
        id="acu_electro", name="전자침술", sub="",
        category="침술", hang="04", mok="01",
        code="40092", unit_price=3980,
    ),
    BillableItemDef(
        id="acu_laser", name="레이저침술", sub="",
        category="침술", hang="04", mok="01",
        code="40100", unit_price=2740,
    ),
    BillableItemDef(
        id="acu_bun", name="분구침술", sub="이침/두침/족침 등",
        category="침술", hang="04", mok="01",
        code="40120", unit_price=2280,
    ),

    # ── 뜸 ──────────────────────────────────────────────────────
    BillableItemDef(
        id="mox_dir_ae", name="구술(직접구-직접애주구)", sub="",
        category="뜸", hang="04", mok="02",
        code="40304", unit_price=5600,
    ),
    BillableItemDef(
        id="mox_dir_sc", name="구술(직접구-반흔구)", sub="",
        category="뜸", hang="04", mok="02",
        code="40305", unit_price=5840,
    ),
    BillableItemDef(
        id="mox_ind_ae", name="구술(간접구-간접애주구)", sub="",
        category="뜸", hang="04", mok="02",
        code="40306", unit_price=2320,
    ),
    BillableItemDef(
        id="mox_ind_dev", name="구술(간접구-기기구술)", sub="",
        category="뜸", hang="04", mok="02",
        code="40307", unit_price=2140,
    ),

    # ── 부항 ────────────────────────────────────────────────────
    BillableItemDef(
        id="cup_wet_1", name="부항술(자락관법)", sub="습식",
        category="부항", hang="04", mok="03",
        code="40312", unit_price=5570,
    ),
    BillableItemDef(
        id="cup_wet_2", name="부항술(자락관법-2부위이상)", sub="습식",
        category="부항", hang="04", mok="03",
        code="40313", unit_price=8350,
    ),
    BillableItemDef(
        id="cup_dry_u", name="부항술(건식-유관법)", sub="건식",
        category="부항", hang="04", mok="03",
        code="40321", unit_price=3470,
    ),
    BillableItemDef(
        id="cup_dry_s", name="부항술(건식-섬관법)", sub="건식",
        category="부항", hang="04", mok="03",
        code="40322", unit_price=3720,
    ),
    BillableItemDef(
        id="cup_dry_j", name="부항술(건식-주관법)", sub="건식",
        category="부항", hang="04", mok="03",
        code="40323", unit_price=4290,
    ),

    # ── 전기/온열 ────────────────────────────────────────────────
    BillableItemDef(
        id="elec_stim", name="침전기자극술", sub="",
        category="전기/온열", hang="04", mok="04",
        code="40091", unit_price=3950,
    ),
    BillableItemDef(
        id="heat_warm", name="온냉경락요법(온열)", sub="경피경근온열요법",
        category="전기/온열", hang="04", mok="04",
        code="40700", unit_price=780,
    ),
    BillableItemDef(
        id="heat_ir", name="온냉경락요법(적외선)", sub="경피적외선조사요법",
        category="전기/온열", hang="04", mok="04",
        code="40701", unit_price=780,
    ),
    BillableItemDef(
        id="heat_cold", name="온냉경락요법(한냉)", sub="경피경근한냉요법",
        category="전기/온열", hang="04", mok="04",
        code="40702", unit_price=780,
    ),

    # ── 추나/도수 ────────────────────────────────────────────────
    BillableItemDef(
        id="chuna_total", name="총관도수법", sub="",
        category="추나/도수", hang="04", mok="05",
        code="45550", unit_price=4940,
    ),
    BillableItemDef(
        id="chuna_attach", name="첩대총관도수법", sub="",
        category="추나/도수", hang="04", mok="05",
        code="45560", unit_price=9370,
    ),
    BillableItemDef(
        id="byeong_jeung", name="변증기술료", sub="",
        category="추나/도수", hang="04", mok="05",
        code="40400", unit_price=2500,
    ),

    # ── 검사 ────────────────────────────────────────────────────
    BillableItemDef(
        id="test_yang", name="양도락검사", sub="",
        category="검사", hang="05", mok="01",
        code="20010", unit_price=3030,
    ),
    BillableItemDef(
        id="test_pulse", name="맥전도검사", sub="",
        category="검사", hang="05", mok="01",
        code="20020", unit_price=2720,
    ),
    BillableItemDef(
        id="test_gyeong", name="경락기능검사", sub="",
        category="검사", hang="05", mok="01",
        code="20030", unit_price=4020,
    ),
    BillableItemDef(
        id="test_gyeong_y", name="경락기능검사(양명경)", sub="",
        category="검사", hang="05", mok="01",
        code="20031", unit_price=3710,
    ),
    BillableItemDef(
        id="test_gyeong_s", name="경락기능검사(수양명경)", sub="",
        category="검사", hang="05", mok="01",
        code="20032", unit_price=3750,
    ),
    BillableItemDef(
        id="test_vertigo", name="현훈검사", sub="",
        category="검사", hang="05", mok="01",
        code="29003", unit_price=3270,
    ),
    BillableItemDef(
        id="test_person", name="인성검사", sub="",
        category="검사", hang="05", mok="01",
        code="29004", unit_price=12900,
    ),
    BillableItemDef(
        id="test_dementia", name="치매검사", sub="",
        category="검사", hang="05", mok="01",
        code="29005", unit_price=22910,
    ),

    # ── 한약조제료 ───────────────────────────────────────────────
    BillableItemDef(
        id="herb_01", name="한약조제료(1일분)", sub="",
        category="한약", hang="11", mok="01",
        code="30010", unit_price=340,
    ),
    BillableItemDef(
        id="herb_02", name="한약조제료(2일분)", sub="",
        category="한약", hang="11", mok="01",
        code="30020", unit_price=420,
    ),
    BillableItemDef(
        id="herb_03", name="한약조제료(3일분)", sub="",
        category="한약", hang="11", mok="01",
        code="30030", unit_price=490,
    ),
    BillableItemDef(
        id="herb_04", name="한약조제료(4일분)", sub="",
        category="한약", hang="11", mok="01",
        code="30040", unit_price=570,
    ),
    BillableItemDef(
        id="herb_05", name="한약조제료(5일분)", sub="",
        category="한약", hang="11", mok="01",
        code="30050", unit_price=650,
    ),
    BillableItemDef(
        id="herb_07", name="한약조제료(7일분)", sub="",
        category="한약", hang="11", mok="01",
        code="30070", unit_price=800,
    ),
    BillableItemDef(
        id="herb_10", name="한약조제료(10일분)", sub="",
        category="한약", hang="11", mok="01",
        code="30100", unit_price=1030,
    ),
    BillableItemDef(
        id="herb_14", name="한약조제료(14일분)", sub="",
        category="한약", hang="11", mok="01",
        code="30140", unit_price=1340,
    ),
    BillableItemDef(
        id="herb_15", name="한약조제료(15일분)", sub="",
        category="한약", hang="11", mok="01",
        code="30150", unit_price=1420,
    ),
    BillableItemDef(
        id="herb_30", name="한약조제료(16~30일분)", sub="",
        category="한약", hang="11", mok="01",
        code="30160", unit_price=1650,
    ),
    BillableItemDef(
        id="herb_60", name="한약조제료(31~60일분)", sub="",
        category="한약", hang="11", mok="01",
        code="30180", unit_price=2030,
    ),
    BillableItemDef(
        id="herb_61p", name="한약조제료(61일분이상)", sub="",
        category="한약", hang="11", mok="01",
        code="30190", unit_price=2340,
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
