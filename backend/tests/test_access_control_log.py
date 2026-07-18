from uuid import UUID

from app.core.config import settings
from app.core.models import AccessControlLog
from sqlalchemy import select

STAFF_DATA = {
    "name": "김간호",
    "username": "nurse01",
    "email": "nurse01@example.com",
    "password": "password1234!!!",
    "role": "nurse",
}


async def test_staff_생성시_부여_기록(client, approved_doctor, db):
    doctor, headers = approved_doctor
    resp = await client.post("/api/staff/", json=STAFF_DATA, headers=headers)
    assert resp.status_code == 201
    staff_id = UUID(resp.json()["id"])

    result = await db.execute(
        select(AccessControlLog).where(AccessControlLog.target_account_id == staff_id)
    )
    log = result.scalar_one()
    assert log.action_type == "부여"
    assert log.reason == "입사"
    assert log.target_account_type == "staff"
    assert log.role == "nurse"
    assert log.acted_by == doctor.id
    assert len(log.acted_at) == 14


async def test_staff_비활성화시_말소_기록(client, approved_doctor, db):
    doctor, headers = approved_doctor
    create_resp = await client.post("/api/staff/", json=STAFF_DATA, headers=headers)
    staff_id = create_resp.json()["id"]

    resp = await client.patch(f"/api/staff/{staff_id}/deactivate", headers=headers)
    assert resp.status_code == 200

    result = await db.execute(
        select(AccessControlLog)
        .where(AccessControlLog.target_account_id == UUID(staff_id))
        .order_by(AccessControlLog.acted_at)
    )
    logs = result.scalars().all()
    assert logs[-1].action_type == "말소"
    assert logs[-1].reason == "퇴사"


async def test_doctor_비활성화시_말소_기록_작업자없음(client):
    reg = await client.post(
        "/api/auth/register",
        json={
            "name": "홍길동",
            "license_number": "99998888",
            "password": "password1234!!!",
            "clinic_name": "테스트한의원",
        },
    )
    doctor_id = reg.json()["doctor_id"]
    await client.post(
        f"/api/auth/admin/approve/{doctor_id}",
        headers={"X-Admin-Key": settings.ADMIN_API_KEY},
    )

    resp = await client.patch(
        f"/api/auth/admin/doctors/{doctor_id}/deactivate",
        headers={"X-Admin-Key": settings.ADMIN_API_KEY},
    )
    assert resp.status_code == 200


async def test_access_control_logs_조회는_owner만(client, approved_doctor):
    doctor, headers = approved_doctor
    await client.post("/api/staff/", json=STAFF_DATA, headers=headers)

    resp = await client.get("/api/auth/access-control-logs", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["action_type"] == "부여"
    assert len(data[0]["acted_at"]) == 14
