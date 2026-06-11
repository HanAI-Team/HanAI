from uuid import UUID

from sqlalchemy import select

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


async def test_recorded_at_없는_기록은_진료이력에_안보임(client, approved_doctor, db):
    from app.core.models import MedicalRecord

    doctor, headers = approved_doctor
    create_resp = await client.post(
        "/api/patients/register", json=PATIENT_DATA, headers=headers
    )
    patient_id = create_resp.json()["id"]

    record = MedicalRecord(
        patient_id=UUID(patient_id),
        doctor_id=doctor.id,
        hospital_id=doctor.hospital_id,
        raw_transcription="두통이 있습니다",
        chart_structured="진단 진행 중",
        status="completed",
    )
    db.add(record)
    await db.commit()

    resp = await client.get(f"/api/patients/{patient_id}/records", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["records"] == []


async def test_create_record_with_medical_history(client, approved_doctor):
    _, headers = approved_doctor
    create_resp = await client.post(
        "/api/patients/register", json=PATIENT_DATA, headers=headers
    )
    patient_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/patients/{patient_id}/records",
        json={
            "chart_structured": "■ 결과 1\n▶ 사상체질\n태음인",
            "raw_transcription": "두통이 있습니다",
            "medical_history": "고혈압 약 복용 중",
        },
        headers=headers,
    )
    assert resp.status_code == 201

    records_resp = await client.get(f"/api/patients/{patient_id}/records", headers=headers)
    record = records_resp.json()["records"][0]
    assert record["raw_transcription"] == "두통이 있습니다"
    assert record["medical_history"] == "고혈압 약 복용 중"


async def test_create_record_with_selected_result(client, approved_doctor, db):
    from app.core.models import MedicalRecord

    _, headers = approved_doctor
    create_resp = await client.post(
        "/api/patients/register", json=PATIENT_DATA, headers=headers
    )
    patient_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/patients/{patient_id}/records",
        json={
            "chart_structured": "■ 결과 1\n▶ 사상체질\n태음인",
            "selected_result": "result1",
        },
        headers=headers,
    )
    assert resp.status_code == 201

    record_id = resp.json()["id"]
    record = (
        await db.execute(select(MedicalRecord).where(MedicalRecord.id == UUID(record_id)))
    ).scalar_one()
    assert record.selected_result == "result1"
