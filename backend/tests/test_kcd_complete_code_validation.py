"""완전코드 목록(KcdUCode) 검증 — update_kcd_code().

기능검사 체크리스트 "착오청구 예방" 세부항목 중 "완전코드 목록 DB"
(청구 불가능한 상위 분류코드/존재하지 않는 코드 차단)를 검증한다.
"""

from datetime import date

import pytest
from fastapi import HTTPException

from app.charting.service import update_kcd_code
from app.core.models import KcdUCode, MedicalRecord, Patient


@pytest.fixture
async def kcd_code(db):
    kcd = KcdUCode(
        code="M5459", korean_name="요통, 상세불명의 부위",
        effective_date=date(2026, 1, 1), expired_date=date(9999, 12, 31),
    )
    db.add(kcd)
    await db.commit()
    return kcd


@pytest.fixture
async def expired_kcd_code(db):
    kcd = KcdUCode(
        code="Z999", korean_name="폐지된 코드",
        effective_date=date(2020, 1, 1), expired_date=date(2021, 1, 1),
    )
    db.add(kcd)
    await db.commit()
    return kcd


async def _make_record(db, doctor):
    patient = Patient(hospital_id=doctor.hospital_id, name="환자", gender="남", insurance_type="health")
    db.add(patient)
    await db.flush()
    record = MedicalRecord(
        patient_id=patient.id, doctor_id=doctor.id, hospital_id=doctor.hospital_id,
        status="completed",
    )
    db.add(record)
    await db.commit()
    return record


async def test_완전코드_목록에_있으면_정상_설정(db, approved_doctor, kcd_code):
    doctor, _ = approved_doctor
    record = await _make_record(db, doctor)
    updated = await update_kcd_code(db, doctor, record.id, "M5459")
    assert updated.kcd_code == "M5459"


async def test_존재하지_않는_코드는_거부(db, approved_doctor):
    doctor, _ = approved_doctor
    record = await _make_record(db, doctor)
    with pytest.raises(HTTPException) as exc:
        await update_kcd_code(db, doctor, record.id, "M54")  # 상위 분류코드(불완전), 완전코드 목록에 없음
    assert exc.value.status_code == 400
    assert "완전코드" in exc.value.detail


async def test_유효기간_지난_코드는_거부(db, approved_doctor, expired_kcd_code):
    doctor, _ = approved_doctor
    record = await _make_record(db, doctor)
    with pytest.raises(HTTPException) as exc:
        await update_kcd_code(db, doctor, record.id, "Z999")
    assert exc.value.status_code == 400
    assert "유효기간" in exc.value.detail


async def test_None으로_초기화는_검증없이_허용(db, approved_doctor):
    doctor, _ = approved_doctor
    record = await _make_record(db, doctor)
    updated = await update_kcd_code(db, doctor, record.id, None)
    assert updated.kcd_code is None
