from datetime import datetime, timezone
from uuid import UUID

import pytest_asyncio

from app.auth.service import create_access_token
from app.core.models import ClaimRejectionCode, Doctor, DrugMaster


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


async def test_list_fees_paginated_and_searchable(client, approved_doctor, fee_master_codes):
    doctor, headers = approved_doctor

    resp = await client.get("/api/fees", params={"page": 1, "size": 3}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 7
    assert data["page"] == 1
    assert data["size"] == 3
    assert len(data["items"]) == 3

    resp = await client.get("/api/fees", params={"search": "체침"}, headers=headers)
    assert resp.status_code == 200
    names = [item["name"] for item in resp.json()["items"]]
    assert all("체침" in n for n in names)
    assert len(names) == 2


async def test_get_fee_single(client, approved_doctor, fee_master_codes):
    doctor, headers = approved_doctor

    resp = await client.get("/api/fees/40121", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "이침술"

    resp = await client.get("/api/fees/NOPE", headers=headers)
    assert resp.status_code == 404


async def test_create_update_delete_fee_requires_owner(client, associate_doctor):
    doctor, headers = associate_doctor
    body = {"code": "ZZ001", "name": "테스트수가", "category": "침술", "unit_price": 5000}

    resp = await client.post("/api/fees", json=body, headers=headers)
    assert resp.status_code == 403


async def test_create_update_delete_fee_as_owner(client, approved_doctor):
    doctor, headers = approved_doctor
    body = {"code": "ZZ001", "name": "테스트수가", "category": "침술", "unit_price": 5000}

    resp = await client.post("/api/fees", json=body, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["unit_price"] == 5000

    resp = await client.post("/api/fees", json=body, headers=headers)
    assert resp.status_code == 409

    resp = await client.patch("/api/fees/ZZ001", json={"unit_price": 6000}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["unit_price"] == 6000

    resp = await client.delete("/api/fees/ZZ001", headers=headers)
    assert resp.status_code == 204

    resp = await client.get("/api/fees/ZZ001", headers=headers)
    assert resp.status_code == 404


async def test_drugs_crud_and_owner_check(client, approved_doctor, associate_doctor, db):
    owner, owner_headers = approved_doctor
    _, staff_headers = associate_doctor
    db.add(DrugMaster(product_code="D001", product_name="테스트약", unit_price=1000))
    await db.commit()

    resp = await client.get("/api/drugs", params={"search": "테스트"}, headers=owner_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 1

    resp = await client.get("/api/drugs/D001", headers=owner_headers)
    assert resp.status_code == 200
    assert resp.json()["product_name"] == "테스트약"

    body = {"product_code": "D002", "product_name": "신약", "unit_price": 2000}
    resp = await client.post("/api/drugs", json=body, headers=staff_headers)
    assert resp.status_code == 403

    resp = await client.post("/api/drugs", json=body, headers=owner_headers)
    assert resp.status_code == 201

    resp = await client.patch("/api/drugs/D002", json={"unit_price": 3000}, headers=owner_headers)
    assert resp.status_code == 200
    assert resp.json()["unit_price"] == 3000

    resp = await client.delete("/api/drugs/D002", headers=owner_headers)
    assert resp.status_code == 204


async def test_rejection_codes_list_filter_create_delete(client, approved_doctor, db):
    owner, headers = approved_doctor
    db.add_all(
        [
            ClaimRejectionCode(category="반송", code="01", detail_code="", description="반송사유1"),
            ClaimRejectionCode(category="심사불능", code="01", detail_code="", description="심사불능사유1"),
        ]
    )
    await db.commit()

    resp = await client.get("/api/rejection-codes", params={"category": "반송"}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["description"] == "반송사유1"
    assert "id" in data["items"][0]

    body = {"category": "반송", "code": "02", "detail_code": "", "description": "신규 반송사유"}
    resp = await client.post("/api/rejection-codes", json=body, headers=headers)
    assert resp.status_code == 201
    new_id = resp.json()["id"]

    resp = await client.post("/api/rejection-codes", json=body, headers=headers)
    assert resp.status_code == 409

    resp = await client.delete(f"/api/rejection-codes/{new_id}", headers=headers)
    assert resp.status_code == 204

    resp = await client.delete(f"/api/rejection-codes/{new_id}", headers=headers)
    assert resp.status_code == 404
