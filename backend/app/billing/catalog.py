"""
차트 화면 우측 패널의 "청구 가능 항목" 목록.

⚠️ 임시(placeholder) 데이터입니다 — 실제 fee_master 테이블 시딩이 되면
이 정적 리스트 대신 DB 조회(fee_master WHERE category='한방진료')로 교체하세요.
"""

from dataclasses import dataclass


@dataclass
class BillableItemDef:
    id: str
    name: str
    sub: str
    hang: str
    mok: str
    code: str          # TODO: 실제 수가코드로 교체 (한방_급여_수가.csv 조회)
    unit_price: float  # TODO: 실제 단가로 교체
    requires_hyeolmyeong: bool = False  # 침술이면 True → 프론트에서 경혈 선택 UI 추가 필요


BILLABLE_CATALOG: list[BillableItemDef] = [
    BillableItemDef(
        id="acupuncture",
        name="침술",
        sub="경혈 선택 필요",
        hang="04", mok="01",
        code="AA200000",
        unit_price=3000.0,
        requires_hyeolmyeong=True,
    ),
    BillableItemDef(
        id="moxibustion",
        name="구술 (뜸)",
        sub="",
        hang="04", mok="02",
        code="AA210000",
        unit_price=2000.0,
    ),
    BillableItemDef(
        id="cupping",
        name="부항술",
        sub="건식부항",
        hang="04", mok="03",
        code="AA220000",
        unit_price=2500.0,
    ),
    BillableItemDef(
        id="electro",
        name="전기침",
        sub="파형/주파수 변경 가능",
        hang="04", mok="04",
        code="AA230000",
        unit_price=2000.0,
    ),
    BillableItemDef(
        id="heat",
        name="온열치료",
        sub="경피적 온열",
        hang="04", mok="04",
        code="AA240000",
        unit_price=1500.0,
    ),
    BillableItemDef(
        id="chuna",
        name="추나치료",
        sub="단순",
        hang="04", mok="04",
        code="AA250000",
        unit_price=15000.0,
    ),
]


def get_catalog_item(item_id: str) -> BillableItemDef:
    for item in BILLABLE_CATALOG:
        if item.id == item_id:
            return item
    raise ValueError(f"정의되지 않은 항목: {item_id}")
