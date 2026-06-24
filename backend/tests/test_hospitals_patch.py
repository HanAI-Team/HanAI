from datetime import datetime, timezone
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


async def test_patch_hospital_by_owner(client, approved_doctor):
    doctor, headers = approved_doctor

    resp = await client.patch(
        f"/api/hospitals/{doctor.hospital_id}",
        json={"name": "수정된병원", "institution_code": "12345678"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "수정된병원"
    assert data["institution_code"] == "12345678"


async def test_patch_hospital_only_updates_provided_fields(client, approved_doctor):
    doctor, headers = approved_doctor

    resp = await client.patch(
        f"/api/hospitals/{doctor.hospital_id}",
        json={"phone": "02-1234-5678"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["phone"] == "02-1234-5678"
    assert data["name"] == "테스트의원"


async def test_patch_hospital_rejects_non_owner(client, associate_doctor):
    doctor, headers = associate_doctor

    resp = await client.patch(
        f"/api/hospitals/{doctor.hospital_id}",
        json={"name": "권한없음"},
        headers=headers,
    )
    assert resp.status_code == 403


async def test_patch_hospital_rejects_other_hospital(client, approved_doctor, db):
    _, headers = approved_doctor

    other_hospital = Hospital(name="다른병원")
    db.add(other_hospital)
    await db.commit()
    await db.refresh(other_hospital)

    resp = await client.patch(
        f"/api/hospitals/{other_hospital.id}",
        json={"name": "침해시도"},
        headers=headers,
    )
    assert resp.status_code == 404
