"""GET /api/kcd/search — 진단 검색. 치과 전용 상병코드(K00~K14) 제외 테스트 포함
(2026-07-16: 실사용 중 "K0522 급성 치관주위염" 같은 치과 코드가 섞여 나온다는
피드백으로 확인 — Zinmac은 한의원 전용 앱이라 치과 코드는 검색에 나오면 안 됨)."""

from datetime import date

import pytest
import pytest_asyncio

from app.core.models import KcdUCode

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def dental_and_general_kcd_codes(db):
    codes = [
        KcdUCode(code="K0522", korean_name="급성 치관주위염", effective_date=date(2000, 1, 1)),
        KcdUCode(code="K0532", korean_name="만성 치관주위염", effective_date=date(2000, 1, 1)),
        KcdUCode(code="K0000", korean_name="부분무치증", effective_date=date(2000, 1, 1)),
        KcdUCode(code="K1401", korean_name="설염", effective_date=date(2000, 1, 1)),
        # K20 이상은 일반 소화기 질환 — 한의과에서도 다루므로 제외 대상 아님
        KcdUCode(code="K291", korean_name="기타 급성 위염", effective_date=date(2000, 1, 1)),
        KcdUCode(code="M5459", korean_name="요통, 상세불명의 부위", effective_date=date(2000, 1, 1)),
    ]
    db.add_all(codes)
    await db.commit()
    return codes


async def test_검색결과에_치과코드_K00_14_제외됨(client, approved_doctor, dental_and_general_kcd_codes):
    _, headers = approved_doctor
    res = await client.get("/api/kcd/search", params={"q": "K0"}, headers=headers)
    assert res.status_code == 200
    codes = [item["code"] for item in res.json()]
    assert "K0522" not in codes
    assert "K0532" not in codes
    assert "K0000" not in codes


async def test_K14는_제외되고_K20은_포함됨(client, approved_doctor, dental_and_general_kcd_codes):
    """K00~K14 경계값 확인 — K14는 치과(제외), K20은 일반 소화기(포함)."""
    _, headers = approved_doctor
    res = await client.get("/api/kcd/search", params={"q": "K1"}, headers=headers)
    codes = [item["code"] for item in res.json()]
    assert "K1401" not in codes

    res2 = await client.get("/api/kcd/search", params={"q": "K2"}, headers=headers)
    codes2 = [item["code"] for item in res2.json()]
    assert "K291" in codes2


async def test_한의과_상병코드_검색_영향없음(client, approved_doctor, dental_and_general_kcd_codes):
    """치과 코드 제외 필터가 무관한 코드(M으로 시작하는 근골격계 등)에는 영향 없어야 한다."""
    _, headers = approved_doctor
    res = await client.get("/api/kcd/search", params={"q": "M5459"}, headers=headers)
    codes = [item["code"] for item in res.json()]
    assert "M5459" in codes


async def test_한글명_검색도_치과코드_제외됨(client, approved_doctor, dental_and_general_kcd_codes):
    _, headers = approved_doctor
    res = await client.get("/api/kcd/search", params={"q": "치관주위염"}, headers=headers)
    assert res.json() == []
