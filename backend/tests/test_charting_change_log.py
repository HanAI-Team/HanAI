from datetime import date, datetime, timedelta, timezone

from app.core.models import Hospital, MedicalRecord, Patient


async def _make_record(db, hospital_id, doctor_id, patient_name, created_at):
    patient = Patient(hospital_id=hospital_id, name=patient_name)
    db.add(patient)
    await db.flush()
    record = MedicalRecord(
        patient_id=patient.id,
        doctor_id=doctor_id,
        hospital_id=hospital_id,
        status="completed",
        created_at=created_at,
        updated_at=created_at,
    )
    db.add(record)
    await db.commit()
    return record, patient


async def test_change_log_lists_own_hospital_records(client, approved_doctor, db):
    doctor, headers = approved_doctor
    now = datetime.now(timezone.utc)
    await _make_record(db, doctor.hospital_id, doctor.id, "환자1", now)
    await _make_record(db, doctor.hospital_id, doctor.id, "환자2", now - timedelta(days=1))

    other_hospital = Hospital(name="다른병원")
    db.add(other_hospital)
    await db.flush()
    await _make_record(db, other_hospital.id, doctor.id, "다른병원환자", now)

    resp = await client.get("/api/charting/change-log", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    names = {item["patient_name"] for item in data["items"]}
    assert names == {"환자1", "환자2"}
    assert "created_at" in data["items"][0]
    assert "updated_at" in data["items"][0]


async def test_change_log_pagination(client, approved_doctor, db):
    doctor, headers = approved_doctor
    now = datetime.now(timezone.utc)
    for i in range(5):
        await _make_record(db, doctor.hospital_id, doctor.id, f"환자{i}", now - timedelta(days=i))

    resp = await client.get("/api/charting/change-log", params={"page": 1, "size": 2}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2


async def test_change_log_date_range_filter(client, approved_doctor, db):
    doctor, headers = approved_doctor
    today = datetime.now(timezone.utc)
    old = today - timedelta(days=10)
    await _make_record(db, doctor.hospital_id, doctor.id, "최근환자", today)
    await _make_record(db, doctor.hospital_id, doctor.id, "오래된환자", old)

    resp = await client.get(
        "/api/charting/change-log",
        params={"date_from": (today - timedelta(days=1)).date().isoformat()},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["patient_name"] == "최근환자"
