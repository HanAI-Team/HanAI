from datetime import datetime, timezone
from uuid import UUID

from app.auth.service import create_access_token
from app.core.models import Doctor, Hospital, Subscription


async def _make_doctor_headers(db, name: str = "김철수"):
    """approved_doctor와 별개로, 스코프 격리 테스트용 '다른 병원' 의사를 만든다."""
    hospital = Hospital(name=f"{name}의원")
    db.add(hospital)
    await db.flush()

    doctor = Doctor(
        hospital_id=hospital.id,
        name=name,
        license_number="99999999",
        password_hash="hashed_password",
        is_approved=True,
        approved_at=datetime.now(timezone.utc),
    )
    db.add(doctor)
    await db.flush()

    db.add(Subscription(hospital_id=hospital.id, tier="basic", status="active"))
    await db.commit()
    await db.refresh(doctor)

    token = create_access_token(
        UUID(str(doctor.id)), UUID(str(doctor.hospital_id)), str(doctor.role)
    )
    return {"Authorization": f"Bearer {token}"}


# ── 생성 ────────────────────────────────────────────────────

async def test_진료일수_생성_성공(client, approved_doctor):
    _, headers = approved_doctor
    resp = await client.post(
        "/api/billing/doctor-work-days",
        json={
            "claim_period_year": 2026,
            "claim_period_month": 7,
            "doctor_birth_date": "800101",
            "work_days": 22,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["claim_period_year"] == 2026
    assert data["claim_period_month"] == 7
    assert data["doctor_birth_date"] == "800101"
    assert data["work_days"] == 22
    assert "id" in data


async def test_진료일수_생년월일_숫자아니면_422(client, approved_doctor):
    _, headers = approved_doctor
    resp = await client.post(
        "/api/billing/doctor-work-days",
        json={
            "claim_period_year": 2026,
            "claim_period_month": 7,
            "doctor_birth_date": "80013O",  # 마지막 글자 알파벳 O
            "work_days": 22,
        },
        headers=headers,
    )
    assert resp.status_code == 422


async def test_진료일수_같은조합_중복생성시_409(client, approved_doctor):
    _, headers = approved_doctor
    payload = {
        "claim_period_year": 2026,
        "claim_period_month": 7,
        "doctor_birth_date": "800101",
        "work_days": 22,
    }
    first = await client.post("/api/billing/doctor-work-days", json=payload, headers=headers)
    assert first.status_code == 201

    dup = await client.post("/api/billing/doctor-work-days", json=payload, headers=headers)
    assert dup.status_code == 409


async def test_진료일수_다른월이면_중복아님(client, approved_doctor):
    _, headers = approved_doctor
    base = {
        "claim_period_year": 2026,
        "doctor_birth_date": "800101",
        "work_days": 22,
    }
    first = await client.post(
        "/api/billing/doctor-work-days", json={**base, "claim_period_month": 7}, headers=headers
    )
    second = await client.post(
        "/api/billing/doctor-work-days", json={**base, "claim_period_month": 8}, headers=headers
    )
    assert first.status_code == 201
    assert second.status_code == 201


# ── 조회 ────────────────────────────────────────────────────

async def test_진료일수_목록_조회(client, approved_doctor):
    _, headers = approved_doctor
    await client.post(
        "/api/billing/doctor-work-days",
        json={
            "claim_period_year": 2026,
            "claim_period_month": 7,
            "doctor_birth_date": "800101",
            "work_days": 22,
        },
        headers=headers,
    )
    await client.post(
        "/api/billing/doctor-work-days",
        json={
            "claim_period_year": 2026,
            "claim_period_month": 6,
            "doctor_birth_date": "850505",
            "work_days": 20,
        },
        headers=headers,
    )

    resp = await client.get("/api/billing/doctor-work-days", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_진료일수_년월_필터(client, approved_doctor):
    _, headers = approved_doctor
    await client.post(
        "/api/billing/doctor-work-days",
        json={
            "claim_period_year": 2026,
            "claim_period_month": 7,
            "doctor_birth_date": "800101",
            "work_days": 22,
        },
        headers=headers,
    )
    await client.post(
        "/api/billing/doctor-work-days",
        json={
            "claim_period_year": 2026,
            "claim_period_month": 6,
            "doctor_birth_date": "850505",
            "work_days": 20,
        },
        headers=headers,
    )

    resp = await client.get(
        "/api/billing/doctor-work-days", params={"year": 2026, "month": 7}, headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["claim_period_month"] == 7


async def test_진료일수_다른병원_데이터는_안보임(client, db, approved_doctor):
    _, headers_a = approved_doctor
    headers_b = await _make_doctor_headers(db, "이영희")

    await client.post(
        "/api/billing/doctor-work-days",
        json={
            "claim_period_year": 2026,
            "claim_period_month": 7,
            "doctor_birth_date": "800101",
            "work_days": 22,
        },
        headers=headers_a,
    )

    resp = await client.get("/api/billing/doctor-work-days", headers=headers_b)
    assert resp.status_code == 200
    assert resp.json() == []


# ── 수정 ────────────────────────────────────────────────────

async def test_진료일수_수정_성공(client, approved_doctor):
    _, headers = approved_doctor
    created = await client.post(
        "/api/billing/doctor-work-days",
        json={
            "claim_period_year": 2026,
            "claim_period_month": 7,
            "doctor_birth_date": "800101",
            "work_days": 22,
        },
        headers=headers,
    )
    work_days_id = created.json()["id"]

    resp = await client.put(
        f"/api/billing/doctor-work-days/{work_days_id}",
        json={"work_days": 15},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["work_days"] == 15


async def test_진료일수_존재하지않는_id_수정시_404(client, approved_doctor):
    _, headers = approved_doctor
    resp = await client.put(
        "/api/billing/doctor-work-days/99999",
        json={"work_days": 10},
        headers=headers,
    )
    assert resp.status_code == 404


async def test_진료일수_다른병원_데이터_수정불가(client, db, approved_doctor):
    _, headers_a = approved_doctor
    headers_b = await _make_doctor_headers(db, "이영희")

    created = await client.post(
        "/api/billing/doctor-work-days",
        json={
            "claim_period_year": 2026,
            "claim_period_month": 7,
            "doctor_birth_date": "800101",
            "work_days": 22,
        },
        headers=headers_a,
    )
    work_days_id = created.json()["id"]

    resp = await client.put(
        f"/api/billing/doctor-work-days/{work_days_id}",
        json={"work_days": 1},
        headers=headers_b,
    )
    assert resp.status_code == 404


# ── 삭제 ────────────────────────────────────────────────────

async def test_진료일수_삭제_성공(client, approved_doctor):
    _, headers = approved_doctor
    created = await client.post(
        "/api/billing/doctor-work-days",
        json={
            "claim_period_year": 2026,
            "claim_period_month": 7,
            "doctor_birth_date": "800101",
            "work_days": 22,
        },
        headers=headers,
    )
    work_days_id = created.json()["id"]

    resp = await client.delete(f"/api/billing/doctor-work-days/{work_days_id}", headers=headers)
    assert resp.status_code == 204

    check = await client.get("/api/billing/doctor-work-days", headers=headers)
    assert check.json() == []


async def test_진료일수_다른병원_데이터_삭제불가(client, db, approved_doctor):
    _, headers_a = approved_doctor
    headers_b = await _make_doctor_headers(db, "이영희")

    created = await client.post(
        "/api/billing/doctor-work-days",
        json={
            "claim_period_year": 2026,
            "claim_period_month": 7,
            "doctor_birth_date": "800101",
            "work_days": 22,
        },
        headers=headers_a,
    )
    work_days_id = created.json()["id"]

    resp = await client.delete(f"/api/billing/doctor-work-days/{work_days_id}", headers=headers_b)
    assert resp.status_code == 404
