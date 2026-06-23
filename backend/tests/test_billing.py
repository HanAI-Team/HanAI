from datetime import date

from app.billing.calculator import calculate_prescription_price
from app.billing.pediatric_dosage import (
    calculate_age_in_months,
    get_pediatric_dosage_ratio,
    get_max_allowed_ratio,
)


# ── pediatric_dosage 단위 테스트 ──────────────────────────────

def test_생후_3개월_미만_비율():
    ref = date(2026, 6, 19)
    birth = date(2026, 3, 19)  # 만 3개월
    assert get_pediatric_dosage_ratio(birth, ref) == 0.2


def test_6개월_이상_1세_미만_비율():
    ref = date(2026, 6, 19)
    birth = date(2025, 10, 1)  # 만 8개월
    assert get_pediatric_dosage_ratio(birth, ref) == 0.25


def test_1세_이상_7세_미만_비율():
    ref = date(2026, 6, 19)
    birth = date(2020, 1, 1)  # 만 6세
    assert get_pediatric_dosage_ratio(birth, ref) == 0.5


def test_7세_이상_11세_미만_비율():
    ref = date(2026, 6, 19)
    birth = date(2017, 1, 1)  # 만 9세
    assert get_pediatric_dosage_ratio(birth, ref) == 0.75


def test_11세_이상은_성인_기준():
    ref = date(2026, 6, 19)
    birth = date(2014, 1, 1)  # 만 12세
    assert get_pediatric_dosage_ratio(birth, ref) == 1.0


def test_생년월일_없으면_성인_기준():
    assert get_pediatric_dosage_ratio(None) == 1.0


def test_최대허용비율은_기본비율의_2배():
    ref = date(2026, 6, 19)
    birth = date(2020, 1, 1)  # 만 6세, 기본 0.5
    assert get_max_allowed_ratio(birth, ref) == 1.0  # 0.5 * 2 = 1.0 (성인 상한 도달)


def test_최대허용비율은_성인_상한을_넘지_않음():
    ref = date(2026, 6, 19)
    birth = date(2017, 1, 1)  # 만 9세, 기본 0.75 -> 2배면 1.5지만 1.0으로 캡
    assert get_max_allowed_ratio(birth, ref) == 1.0


def test_성인은_최대허용비율도_1():
    assert get_max_allowed_ratio(None) == 1.0


def test_만나이_개월수_계산_생일_지남():
    # 2026-06-19 기준 2020-01-01생 -> 77개월 (6년 5개월 18일)
    assert calculate_age_in_months(date(2020, 1, 1), date(2026, 6, 19)) == 77


def test_만나이_개월수_계산_생일_안지남():
    # 2026-06-19 기준 2020-06-25생 -> 아직 6월 생일 안 지남 -> 71개월
    assert calculate_age_in_months(date(2020, 6, 25), date(2026, 6, 19)) == 71


# ── calculator 단위 테스트 ────────────────────────────────────

def test_처방가_기본_계산():
    assert calculate_prescription_price(1800, 1.0, 7) == 12600


def test_소아_비율_적용시_가격_계산():
    assert calculate_prescription_price(1800, 0.5, 7) == 6300


def test_올림_처리_확인():
    # 7 * 0.5 * 3 = 10.5 -> ROUND_UP으로 11
    assert calculate_prescription_price(7, 0.5, 3) == 11


# ── /prescription/check 라우터 테스트 ──────────────────────────

async def test_기준처방은_가감없이_통과(client, approved_doctor):
    _, headers = approved_doctor
    resp = await client.post(
        "/api/billing/prescription/check",
        json={
            "type": "기준처방",
            "herbs": [{"name": "오적산", "dosage_g": 100.0, "role": "base"}],
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["violations"] == []


async def test_가감처방_가미_5종_이하_통과(client, approved_doctor):
    _, headers = approved_doctor
    resp = await client.post(
        "/api/billing/prescription/check",
        json={
            "type": "가감처방",
            "herbs": [
                {"name": "오적산", "dosage_g": 100.0, "role": "base"},
                {"name": "천문동", "dosage_g": 2.0, "role": "added"},
                {"name": "작약", "dosage_g": 1.0, "role": "removed"},
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True


async def test_가감처방_가미_종수_초과시_위반(client, approved_doctor):
    _, headers = approved_doctor
    added = [
        {"name": f"약재{i}", "dosage_g": 1.0, "role": "added"} for i in range(6)
    ]
    resp = await client.post(
        "/api/billing/prescription/check",
        json={"type": "가감처방", "herbs": added},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is False
    assert any("종수 초과" in v["rule"] for v in data["violations"])


async def test_가감처방_가미_용량_초과시_위반(client, approved_doctor):
    _, headers = approved_doctor
    resp = await client.post(
        "/api/billing/prescription/check",
        json={
            "type": "가감처방",
            "herbs": [{"name": "천문동", "dosage_g": 15.0, "role": "added"}],
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is False
    assert any("용량 초과" in v["rule"] for v in data["violations"])


async def test_가감처방_감미와_base는_한도_대상_아님(client, approved_doctor):
    _, headers = approved_doctor
    # removed/base 약재만 잔뜩 있어도 가미(added)가 없으면 위반 없어야 함
    herbs = [
        {"name": "오적산", "dosage_g": 100.0, "role": "base"},
        {"name": "작약", "dosage_g": 50.0, "role": "removed"},
    ]
    resp = await client.post(
        "/api/billing/prescription/check",
        json={"type": "가감처방", "herbs": herbs},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["valid"] is True


async def test_가미제_기존동작_유지_종수초과(client, approved_doctor):
    _, headers = approved_doctor
    herbs = [
        {"name": f"약재{i}", "dosage_g": 1.0, "role": "added"} for i in range(6)
    ]
    resp = await client.post(
        "/api/billing/prescription/check",
        json={"type": "가미제", "herbs": herbs},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is False
    assert any("가미제 종수 초과" in v["rule"] for v in data["violations"])


async def test_임의처방_기존동작_유지_비용초과(client, approved_doctor):
    _, headers = approved_doctor
    herbs = [
        {"name": "약재1", "dosage_g": 5.0, "price_won": 2000.0},
        {"name": "약재2", "dosage_g": 5.0, "price_won": 2000.0},
    ]
    resp = await client.post(
        "/api/billing/prescription/check",
        json={"type": "임의처방", "herbs": herbs},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is False
    assert any("비용 초과" in v["rule"] for v in data["violations"])


async def test_소아환자_가감처방_한도_축소됨(client, approved_doctor):
    """6세 환자(기본비율 0.5, 최대허용비율 1.0)는 성인과 동일 한도이므로
    7세~11세(기본 0.75, 최대허용 1.0으로 캡)와 구분이 어려움.
    대신 6개월 미만(기본 0.2, 최대허용 0.4)으로 명확히 줄어드는 케이스를 검증한다."""
    _, headers = approved_doctor
    resp = await client.post(
        "/api/billing/prescription/check",
        json={
            "type": "가감처방",
            "herbs": [{"name": "천문동", "dosage_g": 5.0, "role": "added"}],
            "patient_birth_date": "2026-03-19",  # 기준일 근처 3개월 영아
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    # 4g(=10g*0.4) 한도 초과이므로 위반이어야 함
    assert data["valid"] is False
    assert any("용량 초과" in v["rule"] for v in data["violations"])


async def test_성인환자는_한도_그대로_적용(client, approved_doctor):
    _, headers = approved_doctor
    resp = await client.post(
        "/api/billing/prescription/check",
        json={
            "type": "가감처방",
            "herbs": [{"name": "천문동", "dosage_g": 9.0, "role": "added"}],
            "patient_birth_date": None,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["valid"] is True
