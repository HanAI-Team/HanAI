PATIENT_DATA = {
    "name": "김환자",
    "birth_date": "1990-01-01",
    "gender": "M",
    "phone": "010-1234-5678",
}


async def test_create_patient_success(client, approved_doctor):
    _, headers = approved_doctor
    resp = await client.post("/api/patients/register", json=PATIENT_DATA, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "김환자"
    assert "id" in data


async def test_get_patients_empty(client, approved_doctor):
    _, headers = approved_doctor
    resp = await client.get("/api/patients/", headers=headers)
    assert resp.status_code == 404


async def test_get_patients_with_data(client, approved_doctor):
    _, headers = approved_doctor
    await client.post("/api/patients/register", json=PATIENT_DATA, headers=headers)

    resp = await client.get("/api/patients/", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


async def test_get_patient_detail(client, approved_doctor):
    _, headers = approved_doctor
    create_resp = await client.post(
        "/api/patients/register", json=PATIENT_DATA, headers=headers
    )
    patient_id = create_resp.json()["id"]

    resp = await client.get(f"/api/patients/{patient_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == patient_id


async def test_get_patient_not_found(client, approved_doctor):
    _, headers = approved_doctor
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = await client.get(f"/api/patients/{fake_id}", headers=headers)
    assert resp.status_code == 404


async def test_update_patient(client, approved_doctor):
    _, headers = approved_doctor
    create_resp = await client.post(
        "/api/patients/register", json=PATIENT_DATA, headers=headers
    )
    patient_id = create_resp.json()["id"]

    resp = await client.put(
        f"/api/patients/{patient_id}",
        json={"phone": "010-9999-9999", "memo": "수정됨"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["phone"] == "010-9999-9999"
    assert data["memo"] == "수정됨"


async def test_get_patient_records_empty(client, approved_doctor):
    _, headers = approved_doctor
    create_resp = await client.post(
        "/api/patients/register", json=PATIENT_DATA, headers=headers
    )
    patient_id = create_resp.json()["id"]

    resp = await client.get(f"/api/patients/{patient_id}/records", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["records"] == []
