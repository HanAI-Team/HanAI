import pytest
from app.auth import router as auth_router
from app.core.config import settings

REGISTER_DATA = {
    "name": "홍길동",
    "license_number": "12345678",
    "password": "password1234!!!",
    "clinic_name": "테스트의원",
}


class _FakeRedis:
    """login 잠금 로직(get/incr/expire/set/delete)만 흉내내는 메모리 기반 가짜 redis."""

    def __init__(self):
        self._store = {}

    def get(self, key):
        return self._store.get(key)

    def incr(self, key):
        self._store[key] = int(self._store.get(key, 0)) + 1
        return self._store[key]

    def expire(self, key, seconds):
        pass

    def set(self, key, value, ex=None):
        self._store[key] = value

    def delete(self, key):
        self._store.pop(key, None)

    def llen(self, key):
        return len(self._store.get(key, []))

    def lpop(self, key):
        lst = self._store.get(key)
        if not lst:
            return None
        return lst.pop(0)

    def rpush(self, key, value):
        self._store.setdefault(key, []).append(value)
        return len(self._store[key])

    def lrange(self, key, start, end):
        lst = self._store.get(key, [])
        if end == -1:
            return lst[start:]
        return lst[start : end + 1]


@pytest.fixture
def fake_redis(monkeypatch):
    redis = _FakeRedis()
    monkeypatch.setattr(auth_router, "_redis", redis)
    import app.core.redis as core_redis
    monkeypatch.setattr(core_redis, "_redis", redis)
    return redis

async def _register_and_approve(client) -> None:
    reg = await client.post("/api/auth/register", json=REGISTER_DATA)
    doctor_id = reg.json()["doctor_id"]
    await client.post(
        f"/api/auth/admin/approve/{doctor_id}",
        headers={"X-Admin-Key": settings.ADMIN_API_KEY},
    )


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
    resp = await client.post("/api/auth/login", json={"license_number": "99999999", "password": "password1234!!!"})
    assert resp.status_code == 401


async def test_login_not_approved(client):
    await client.post("/api/auth/register", json=REGISTER_DATA)
    resp = await client.post("/api/auth/login", json={"license_number": "12345678", "password": "password1234!!!"})
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

    resp = await client.post("/api/auth/login", json={"license_number": "12345678", "password": "password1234!!!"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_로그인_5회_실패시_잠금(client, fake_redis):
    await _register_and_approve(client)

    for _ in range(4):
        resp = await client.post(
            "/api/auth/login",
            json={"license_number": "12345678", "password": "wrong-password"},
        )
        assert resp.status_code == 401

    resp = await client.post(
        "/api/auth/login",
        json={"license_number": "12345678", "password": "wrong-password"},
    )
    assert resp.status_code == 403
    assert "잠겼습니다" in resp.json()["detail"]


async def test_잠긴_상태에서_재시도시_403(client, fake_redis):
    await _register_and_approve(client)

    for _ in range(5):
        await client.post(
            "/api/auth/login",
            json={"license_number": "12345678", "password": "wrong-password"},
        )

    # 비밀번호가 맞아도 잠금 상태면 403
    resp = await client.post(
        "/api/auth/login",
        json={"license_number": "12345678", "password": "password1234!!!"},
    )
    assert resp.status_code == 403


async def test_성공_로그인_후_실패카운터_초기화(client, fake_redis):
    await _register_and_approve(client)

    for _ in range(3):
        await client.post(
            "/api/auth/login",
            json={"license_number": "12345678", "password": "wrong-password"},
        )

    resp = await client.post(
        "/api/auth/login",
        json={"license_number": "12345678", "password": "password1234!!!"},
    )
    assert resp.status_code == 200

    # 카운터가 초기화됐다면 다시 실패해도 남은 시도는 4회(=1회차)여야 함
    resp = await client.post(
        "/api/auth/login",
        json={"license_number": "12345678", "password": "wrong-password"},
    )
    assert resp.status_code == 401
    assert "남은 시도: 4회" in resp.json()["detail"]
