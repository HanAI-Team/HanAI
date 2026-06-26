import pytest

pytestmark = pytest.mark.asyncio


async def test_분구침술_2개_동시청구_불가(client, approved_doctor, fee_master_codes):
    _, headers = approved_doctor
    res = await client.post(
        "/api/acupuncture/check-concurrent",
        json={"codes": ["40121", "40122"]},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is False
    assert "40121" in data["conflicting_codes"]
    assert "40122" in data["conflicting_codes"]


async def test_분구침술_1개만_단독청구_통과(client, approved_doctor, fee_master_codes):
    _, headers = approved_doctor
    res = await client.post(
        "/api/acupuncture/check-concurrent",
        json={"codes": ["40121"]},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["conflicting_codes"] == []


async def test_일반침술만_청구_통과(client, approved_doctor, fee_master_codes):
    _, headers = approved_doctor
    res = await client.post(
        "/api/acupuncture/check-concurrent",
        json={"codes": ["40001"]},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True


async def test_분구침술과_일반침술_혼합시_통과(client, approved_doctor, fee_master_codes):
    """분구침술 1개 + 일반침술은 청구 가능 (분구침술 2개 이상일 때만 불가)."""
    _, headers = approved_doctor
    res = await client.post(
        "/api/acupuncture/check-concurrent",
        json={"codes": ["40121", "40001"]},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True


async def test_빈_목록_통과(client, approved_doctor, fee_master_codes):
    _, headers = approved_doctor
    res = await client.post(
        "/api/acupuncture/check-concurrent",
        json={"codes": []},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True


async def test_인증없으면_401(client, fee_master_codes):
    res = await client.post(
        "/api/acupuncture/check-concurrent",
        json={"codes": ["40121"]},
    )
    assert res.status_code == 401

async def test_침술_3종_이내_통과(client, approved_doctor, fee_master_codes):
    _, headers = approved_doctor
    res = await client.post(
        "/api/acupuncture/check-daily-limit",
        json={"codes": ["AA159", "AA161", "AA163"]},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["excess_count"] == 3


async def test_침술_3종_초과_불가(client, approved_doctor, fee_master_codes):
    _, headers = approved_doctor
    res = await client.post(
        "/api/acupuncture/check-daily-limit",
        json={"codes": ["AA159", "AA161", "AA163", "AA165"]},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is False
    assert data["excess_count"] == 4


async def test_침술_1종만_통과(client, approved_doctor, fee_master_codes):
    _, headers = approved_doctor
    res = await client.post(
        "/api/acupuncture/check-daily-limit",
        json={"codes": ["AA159"]},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True


async def test_침술_빈목록_통과(client, approved_doctor, fee_master_codes):
    _, headers = approved_doctor
    res = await client.post(
        "/api/acupuncture/check-daily-limit",
        json={"codes": []},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True


async def test_침술_daily_limit_인증없으면_401(client, fee_master_codes):
    res = await client.post(
        "/api/acupuncture/check-daily-limit",
        json={"codes": ["AA159"]},
    )
    assert res.status_code == 401

async def test_특수침술_2종_이내_통과(client, approved_doctor, fee_master_codes):
    _, headers = approved_doctor
    res = await client.post(
        "/api/acupuncture/check-special-limit",
        json={"codes": ["40030", "40040"]},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["excess_count"] == 2


async def test_특수침술_3종_초과_불가(client, approved_doctor, fee_master_codes):
    _, headers = approved_doctor
    res = await client.post(
        "/api/acupuncture/check-special-limit",
        json={"codes": ["40030", "40040", "40050"]},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is False
    assert data["excess_count"] == 3


async def test_특수침술_1종만_통과(client, approved_doctor, fee_master_codes):
    _, headers = approved_doctor
    res = await client.post(
        "/api/acupuncture/check-special-limit",
        json={"codes": ["40030"]},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True


async def test_특수침술_일반침술_혼합시_특수만_카운트(client, approved_doctor, fee_master_codes):
    """일반침술 코드는 특수침술 카운트에서 제외."""
    _, headers = approved_doctor
    res = await client.post(
        "/api/acupuncture/check-special-limit",
        json={"codes": ["40030", "40040", "AA159"]},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["excess_count"] == 2


async def test_특수침술_빈목록_통과(client, approved_doctor, fee_master_codes):
    _, headers = approved_doctor
    res = await client.post(
        "/api/acupuncture/check-special-limit",
        json={"codes": []},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True


async def test_특수침술_인증없으면_401(client, fee_master_codes):
    res = await client.post(
        "/api/acupuncture/check-special-limit",
        json={"codes": ["40030"]},
    )
    assert res.status_code == 401
