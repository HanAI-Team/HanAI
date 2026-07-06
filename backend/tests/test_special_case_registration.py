from datetime import date, timedelta

import pytest

from app.billing.service import SpecialCaseResolution, create_claim, resolve_active_special_code
from app.core.models import Hospital, MedicalRecord, MedicalRecordProcedure, Patient, SpecialCaseRegistration

pytestmark = pytest.mark.asyncio


async def _make_patient(db, hospital) -> Patient:
    patient = Patient(hospital_id=hospital.id, name="환자", gender="남")
    db.add(patient)
    await db.flush()
    return patient


async def _make_hospital(db) -> Hospital:
    hospital = Hospital(name="테스트병원")
    db.add(hospital)
    await db.flush()
    return hospital


async def test_등록없으면_None(db):
    hospital = await _make_hospital(db)
    patient = await _make_patient(db, hospital)
    await db.commit()

    result = await resolve_active_special_code(db, patient.id)
    assert result == SpecialCaseResolution(special_code=None, needs_review=False)


async def test_단일_활성등록_반환(db):
    hospital = await _make_hospital(db)
    patient = await _make_patient(db, hospital)
    db.add(SpecialCaseRegistration(
        patient_id=patient.id, special_code="V193", category="암",
        registered_at=date(2026, 1, 1),
    ))
    await db.commit()

    result = await resolve_active_special_code(db, patient.id)
    assert result.special_code == "V193"
    assert result.needs_review is False


async def test_cancelled_제외(db):
    hospital = await _make_hospital(db)
    patient = await _make_patient(db, hospital)
    db.add(SpecialCaseRegistration(
        patient_id=patient.id, special_code="V193", category="암",
        registered_at=date(2026, 1, 1), status="cancelled",
    ))
    await db.commit()

    result = await resolve_active_special_code(db, patient.id)
    assert result.special_code is None


async def test_expires_at_지난등록_제외(db):
    hospital = await _make_hospital(db)
    patient = await _make_patient(db, hospital)
    db.add(SpecialCaseRegistration(
        patient_id=patient.id, special_code="V193", category="암",
        registered_at=date(2020, 1, 1),
        expires_at=date.today() - timedelta(days=1),
    ))
    await db.commit()

    result = await resolve_active_special_code(db, patient.id)
    assert result.special_code is None


async def test_expires_at_없으면_계속_활성(db):
    hospital = await _make_hospital(db)
    patient = await _make_patient(db, hospital)
    db.add(SpecialCaseRegistration(
        patient_id=patient.id, special_code="V000", category="결핵",
        registered_at=date(2020, 1, 1), expires_at=None,
    ))
    await db.commit()

    result = await resolve_active_special_code(db, patient.id)
    assert result.special_code == "V000"
    assert result.needs_review is False


async def test_여러건_활성시_본인부담률_최저값_우선(db):
    hospital = await _make_hospital(db)
    patient = await _make_patient(db, hospital)
    db.add_all([
        SpecialCaseRegistration(
            patient_id=patient.id, special_code="V193", category="암",
            registered_at=date(2026, 1, 1),
        ),
        SpecialCaseRegistration(
            patient_id=patient.id, special_code="V000", category="결핵",
            registered_at=date(2026, 1, 1),
        ),
    ])
    await db.commit()

    # V000(결핵)=0% < V193(암)=5%
    result = await resolve_active_special_code(db, patient.id)
    assert result.special_code == "V000"
    assert result.needs_review is False


async def test_확인필요항목보다_확정된_낮은값_우선(db):
    hospital = await _make_hospital(db)
    patient = await _make_patient(db, hospital)
    db.add_all([
        SpecialCaseRegistration(
            patient_id=patient.id, special_code="V191", category="뇌혈관",  # 확인 필요, 19%
            registered_at=date(2026, 1, 1),
        ),
        SpecialCaseRegistration(
            patient_id=patient.id, special_code="V027", category="희귀난치",  # 확정 10%
            registered_at=date(2026, 1, 1),
        ),
    ])
    await db.commit()

    result = await resolve_active_special_code(db, patient.id)
    assert result.special_code == "V027"
    assert result.needs_review is False


async def test_확인필요항목만_있어도_반환되고_플래그_켜짐(db):
    hospital = await _make_hospital(db)
    patient = await _make_patient(db, hospital)
    db.add(SpecialCaseRegistration(
        patient_id=patient.id, special_code="F006", category="신체기능저하군",
        registered_at=date(2026, 1, 1),
    ))
    await db.commit()

    result = await resolve_active_special_code(db, patient.id)
    assert result.special_code == "F006"
    assert result.needs_review is True


async def test_V221_근거없어_확인필요로_분류됨(db):
    """copayment.py._special_rate는 V221=5%로 두지만 근거(고시 번호 등)가
    코드/커밋 이력에 없어 needs_review 대상으로 재분류했다."""
    hospital = await _make_hospital(db)
    patient = await _make_patient(db, hospital)
    db.add(SpecialCaseRegistration(
        patient_id=patient.id, special_code="V221", category="중증화상",
        registered_at=date(2026, 1, 1),
    ))
    await db.commit()

    result = await resolve_active_special_code(db, patient.id)
    assert result.special_code == "V221"
    assert result.needs_review is True


async def test_create_claim_활성_산정특례_있으면_낮은본인부담률_적용(db, approved_doctor, kcd_codes):
    """create_claim()이 resolve_active_special_code()를 실제로 반영하는지 확인 (기존 공백 메꿈)."""
    doctor, _ = approved_doctor
    hospital = await db.get(Hospital, doctor.hospital_id)

    patient = Patient(hospital_id=hospital.id, name="암환자", gender="남", insurance_type="health")
    db.add(patient)
    await db.flush()

    db.add(SpecialCaseRegistration(
        patient_id=patient.id, special_code="V193", category="암",
        registered_at=date(2026, 1, 1),
    ))

    record = MedicalRecord(
        patient_id=patient.id, doctor_id=doctor.id, hospital_id=hospital.id,
        kcd_code="B001", chart_structured="일반 진료", status="completed",
    )
    db.add(record)
    await db.flush()

    db.add(MedicalRecordProcedure(medical_record_id=record.id, procedure_type="진료", amount=100000))
    await db.commit()

    claim = await create_claim(
        db=db, hospital_id=hospital.id, doctor_id=doctor.id, patient_id=patient.id,
        medical_record_ids=[record.id], claim_period_year=2026, claim_period_month=6,
        visit_type="외래",
    )

    # V193(암)=5% → ceil(100000*0.05)=5000. 산정특례 미반영이면 건강보험 외래 일반 30%=30000이 됐을 것.
    assert claim.patient_copay == 5000
    assert claim.special_case_needs_review is False


async def test_create_claim_확인필요_산정특례는_플래그_노출(db, approved_doctor, kcd_codes):
    doctor, _ = approved_doctor
    hospital = await db.get(Hospital, doctor.hospital_id)

    patient = Patient(hospital_id=hospital.id, name="뇌혈관환자", gender="남", insurance_type="health")
    db.add(patient)
    await db.flush()

    db.add(SpecialCaseRegistration(
        patient_id=patient.id, special_code="V191", category="뇌혈관",
        registered_at=date(2026, 1, 1),
    ))

    record = MedicalRecord(
        patient_id=patient.id, doctor_id=doctor.id, hospital_id=hospital.id,
        kcd_code="B001", chart_structured="일반 진료", status="completed",
    )
    db.add(record)
    await db.flush()

    db.add(MedicalRecordProcedure(medical_record_id=record.id, procedure_type="진료", amount=100000))
    await db.commit()

    claim = await create_claim(
        db=db, hospital_id=hospital.id, doctor_id=doctor.id, patient_id=patient.id,
        medical_record_ids=[record.id], claim_period_year=2026, claim_period_month=6,
        visit_type="외래",
    )

    assert claim.special_case_needs_review is True


async def test_calculate_엔드포인트_patient_id_있으면_DB조회값이_body_special_code보다_우선(
    client, approved_doctor, db
):
    doctor, headers = approved_doctor
    hospital = await db.get(Hospital, doctor.hospital_id)

    patient = Patient(hospital_id=hospital.id, name="암환자", gender="남", insurance_type="health")
    db.add(patient)
    await db.flush()
    db.add(SpecialCaseRegistration(
        patient_id=patient.id, special_code="V193", category="암",
        registered_at=date(2026, 1, 1),
    ))
    await db.commit()

    resp = await client.post(
        "/api/billing/calculate",
        json={
            "insurance_type": "4",
            "visit_type": "외래",
            "benefit_total": 100000,
            "patient_id": str(patient.id),
            "special_code": "C001",  # DB 조회값(V193)이 있으면 이 값은 무시돼야 함
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["special_code"] == "V193"
    assert data["needs_review"] is False
    assert data["copayment"] == 5000  # ceil(100000*0.05)


async def test_calculate_엔드포인트_patient_id_없으면_기존처럼_body_special_code_사용(
    client, approved_doctor
):
    _, headers = approved_doctor

    resp = await client.post(
        "/api/billing/calculate",
        json={
            "insurance_type": "4",
            "visit_type": "외래",
            "benefit_total": 100000,
            "special_code": "V027",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["special_code"] == "V027"
    assert data["needs_review"] is False
    assert data["copayment"] == 10000  # ceil(100000*0.10)
