from datetime import date, datetime, timezone
from uuid import UUID

import pytest_asyncio

from app.auth.service import create_access_token
from app.core.models import Doctor, Hospital


@pytest_asyncio.fixture
async def associate_doctor(db, approved_doctor):
    owner, _ = approved_doctor
    doctor = Doctor(
        hospital_id=owner.hospital_id,
        name="부원장",
        license_number="11112222",
        password_hash="hashed_password",
        role="associate",
        is_approved=True,
        approved_at=datetime.now(timezone.utc),
    )
    db.add(doctor)
    await db.commit()
    await db.refresh(doctor)

    token = create_access_token(
        UUID(str(doctor.id)), UUID(str(doctor.hospital_id)), "associate"
    )
    return doctor, {"Authorization": f"Bearer {token}"}


async def test_create_doctor_work_days_생년월일_미등록시_차단(client, approved_doctor):
    doctor, headers = approved_doctor

    resp = await client.post(
        f"/api/hospitals/{doctor.hospital_id}/doctor-work-days",
        json={
            "doctor_id": str(doctor.id),
            "claim_period_year": 2026,
            "claim_period_month": 6,
            "work_days": 22,
        },
        headers=headers,
    )
    assert resp.status_code == 400
    assert "생년월일" in resp.json()["detail"]
    assert "/api/auth/me" in resp.json()["detail"]


async def test_create_doctor_work_days_생년월일_등록후_자동조회(client, approved_doctor):
    doctor, headers = approved_doctor

    await client.patch(
        "/api/auth/me", json={"birth_date": "1985-03-20"}, headers=headers
    )

    resp = await client.post(
        f"/api/hospitals/{doctor.hospital_id}/doctor-work-days",
        json={
            "doctor_id": str(doctor.id),
            "claim_period_year": 2026,
            "claim_period_month": 6,
            "work_days": 22,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["doctor_birth_date"] == "850320"
    assert data["work_days"] == 22


async def test_create_doctor_work_days_upsert(client, approved_doctor):
    doctor, headers = approved_doctor
    await client.patch(
        "/api/auth/me", json={"birth_date": "1985-03-20"}, headers=headers
    )
    body = {
        "doctor_id": str(doctor.id),
        "claim_period_year": 2026,
        "claim_period_month": 6,
        "work_days": 22,
    }
    await client.post(
        f"/api/hospitals/{doctor.hospital_id}/doctor-work-days", json=body, headers=headers
    )

    body["work_days"] = 15
    resp = await client.post(
        f"/api/hospitals/{doctor.hospital_id}/doctor-work-days", json=body, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["work_days"] == 15

    list_resp = await client.get(
        f"/api/hospitals/{doctor.hospital_id}/doctor-work-days", headers=headers
    )
    assert len(list_resp.json()) == 1
    assert list_resp.json()[0]["work_days"] == 15


async def test_create_doctor_work_days_rejects_non_owner(client, associate_doctor):
    doctor, headers = associate_doctor

    resp = await client.post(
        f"/api/hospitals/{doctor.hospital_id}/doctor-work-days",
        json={
            "doctor_id": str(doctor.id),
            "claim_period_year": 2026,
            "claim_period_month": 6,
            "work_days": 22,
        },
        headers=headers,
    )
    assert resp.status_code == 403


async def test_create_doctor_work_days_rejects_other_hospital_doctor(
    client, approved_doctor, db
):
    doctor, headers = approved_doctor

    other_hospital = Hospital(name="다른병원")
    db.add(other_hospital)
    await db.flush()
    other_doctor = Doctor(
        hospital_id=other_hospital.id,
        name="타병원의사",
        license_number="99998888",
        password_hash="hashed_password",
        is_approved=True,
        birth_date=date(1990, 1, 1),
    )
    db.add(other_doctor)
    await db.commit()
    await db.refresh(other_doctor)

    resp = await client.post(
        f"/api/hospitals/{doctor.hospital_id}/doctor-work-days",
        json={
            "doctor_id": str(other_doctor.id),
            "claim_period_year": 2026,
            "claim_period_month": 6,
            "work_days": 22,
        },
        headers=headers,
    )
    assert resp.status_code == 404
