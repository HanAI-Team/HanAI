from app.core.config import settings

REGISTER_DATA = {
    "name": "홍길동",
    "license_number": "12345678",
    "clinic_name": "테스트의원",
}


async def test_register_success(client):
    resp = await client.post("/api/auth/register", json=REGISTER_DATA)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "홍길동"
    assert "doctor_id" in data


async def test_register_invalid_license(client):
    resp = await client.post(
        "/api/auth/register", json={**REGISTER_DATA, "license_number": "INVALID"}
    )
    assert resp.status_code == 422


async def test_register_duplicate_license(client):
    await client.post("/api/auth/register", json=REGISTER_DATA)
    resp = await client.post("/api/auth/register", json=REGISTER_DATA)
    assert resp.status_code == 409


async def test_login_not_found(client):
    resp = await client.post("/api/auth/login", json={"license_number": "99999999"})
    assert resp.status_code == 401


async def test_login_not_approved(client):
    await client.post("/api/auth/register", json=REGISTER_DATA)
    resp = await client.post("/api/auth/login", json={"license_number": "12345678"})
    assert resp.status_code == 403


async def test_admin_approve_success(client):
    reg = await client.post("/api/auth/register", json=REGISTER_DATA)
    doctor_id = reg.json()["doctor_id"]

    resp = await client.post(
        f"/api/auth/admin/approve/{doctor_id}",
        headers={"X-Admin-Key": settings.ADMIN_API_KEY},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data


async def test_admin_approve_invalid_key(client):
    reg = await client.post("/api/auth/register", json=REGISTER_DATA)
    doctor_id = reg.json()["doctor_id"]

    resp = await client.post(
        f"/api/auth/admin/approve/{doctor_id}",
        headers={"X-Admin-Key": "wrong-key"},
    )
    # 구현상 403 반환 (잘못된 관리자 키)
    assert resp.status_code == 403


async def test_login_success(client):
    reg = await client.post("/api/auth/register", json=REGISTER_DATA)
    doctor_id = reg.json()["doctor_id"]

    await client.post(
        f"/api/auth/admin/approve/{doctor_id}",
        headers={"X-Admin-Key": settings.ADMIN_API_KEY},
    )

    resp = await client.post("/api/auth/login", json={"license_number": "12345678"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
