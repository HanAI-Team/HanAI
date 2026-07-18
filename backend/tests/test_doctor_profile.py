async def test_patch_me_updates_birth_date(client, approved_doctor):
    doctor, headers = approved_doctor

    resp = await client.patch(
        "/api/auth/me",
        json={"birth_date": "1985-03-20"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["birth_date"] == "1985-03-20"

    resp = await client.get("/api/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["birth_date"] == "1985-03-20"


async def test_patch_me_requires_auth(client):
    resp = await client.patch("/api/auth/me", json={"birth_date": "1985-03-20"})
    assert resp.status_code in (401, 403)


# ── 생년월일 유효성 검증 (2026-07-16 추가) ────────────────────────────────
# SAM/EDI H010 작성자생년월일에 그대로 들어가는 값이라, 요양기관기호와
# 마찬가지로 오타/미래날짜가 들어가면 청구파일이 반려될 수 있어 검증을 추가.

async def test_생년월일_미래날짜는_거부(client, approved_doctor):
    doctor, headers = approved_doctor
    resp = await client.patch(
        "/api/auth/me",
        json={"birth_date": "2099-01-01"},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_생년월일_100년이상_과거는_거부(client, approved_doctor):
    doctor, headers = approved_doctor
    resp = await client.patch(
        "/api/auth/me",
        json={"birth_date": "1900-01-01"},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_생년월일_null로_보내면_기존값_유지(client, approved_doctor):
    """이미 설정된 생년월일을 null로 지우려는 시도는 무시하고 기존 값을 유지한다."""
    doctor, headers = approved_doctor
    await client.patch("/api/auth/me", json={"birth_date": "1985-03-20"}, headers=headers)

    resp = await client.patch("/api/auth/me", json={"birth_date": None}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["birth_date"] == "1985-03-20"
