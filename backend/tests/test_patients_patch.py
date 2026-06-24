from datetime import datetime, timezone
from uuid import UUID

import pytest_asyncio

from app.auth.service import create_access_token
from app.core.models import Doctor, Hospital, StaffAccount

PATIENT_DATA = {
    "name": "김환자",
    "birth_date": "1990-01-01",
    "gender": "M",
    "phone": "010-1234-5678",
}


@pytest_asyncio.fixture
async def staff_account(db, approved_doctor):
    doctor, _ = approved_doctor
    staff = StaffAccount(
        hospital_id=doctor.hospital_id,
        name="간호사",
        username="nurse1",
        password_hash="hashed_password",
        role="nurse",
    )
    db.add(staff)
    await db.commit()
    await db.refresh(staff)

    token = create_access_token(
        UUID(str(staff.id)), UUID(str(staff.hospital_id)), "nurse"
    )
    return staff, {"Authorization": f"Bearer {token}"}


async def test_patch_patient_by_doctor(client, approved_doctor):
    _, headers = approved_doctor
    create_resp = await client.post(
        "/api/patients/register", json=PATIENT_DATA, headers=headers
    )
    patient_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/patients/{patient_id}",
        json={"name": "김환자수정", "rrn": "900101-1234567", "insurance_type": "care"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "김환자수정"


async def test_patch_patient_only_updates_provided_fields(client, approved_doctor):
    _, headers = approved_doctor
    create_resp = await client.post(
        "/api/patients/register", json=PATIENT_DATA, headers=headers
    )
    patient_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/patients/{patient_id}",
        json={"memo": "메모만 수정"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["memo"] == "메모만 수정"
    assert data["name"] == "김환자"
    assert data["phone"] == "010-1234-5678"


async def test_patch_patient_by_staff(client, approved_doctor, staff_account):
    _, doctor_headers = approved_doctor
    create_resp = await client.post(
        "/api/patients/register", json=PATIENT_DATA, headers=doctor_headers
    )
    patient_id = create_resp.json()["id"]

    _, staff_headers = staff_account
    resp = await client.patch(
        f"/api/patients/{patient_id}",
        json={"phone": "010-0000-0000"},
        headers=staff_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["phone"] == "010-0000-0000"


async def test_patch_patient_rejects_other_hospital(client, approved_doctor, db):
    _, headers = approved_doctor
    create_resp = await client.post(
        "/api/patients/register", json=PATIENT_DATA, headers=headers
    )
    patient_id = create_resp.json()["id"]

    other_hospital = Hospital(name="다른의원")
    db.add(other_hospital)
    await db.flush()
    other_doctor = Doctor(
        hospital_id=other_hospital.id,
        name="이의사",
        license_number="87654321",
        password_hash="hashed_password",
        is_approved=True,
        approved_at=datetime.now(timezone.utc),
    )
    db.add(other_doctor)
    await db.commit()
    await db.refresh(other_doctor)

    other_token = create_access_token(
        UUID(str(other_doctor.id)), UUID(str(other_doctor.hospital_id)), str(other_doctor.role)
    )
    other_headers = {"Authorization": f"Bearer {other_token}"}

    resp = await client.patch(
        f"/api/patients/{patient_id}",
        json={"memo": "침해시도"},
        headers=other_headers,
    )
    assert resp.status_code == 404
