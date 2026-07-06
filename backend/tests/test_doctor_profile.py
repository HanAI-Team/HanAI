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
