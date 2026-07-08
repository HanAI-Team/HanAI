"""추나요법 사전교육 이수여부 검증 테스트 (2026-07-08 신규).

- 프로필 PATCH/GET으로 이수여부·배너 필드가 정상 저장/조회되는지
- notice_rules.py의 순수 함수 단위 검증 (ERROR 발생 조건)
- create_claim() 통합 — 실제로 청구가 차단/통과되는지
"""

from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from app.billing.notice_rules import validate_notice_rules
from app.billing.service import create_claim
from app.core.models import Hospital, MedicalRecord, MedicalRecordProcedure, Patient, FeeMaster

pytestmark = pytest.mark.asyncio


# ── 1. 프로필 PATCH/GET ────────────────────────────────────────────

async def test_PATCH_me_이수여부_변경(client, approved_doctor):
    _, headers = approved_doctor
    resp = await client.patch(
        "/api/auth/me",
        json={"chuna_training_certified": True},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["chuna_training_certified"] is True


async def test_PATCH_me_배너_확인_변경(client, approved_doctor):
    _, headers = approved_doctor
    resp = await client.patch(
        "/api/auth/me",
        json={"chuna_training_banner_seen": True},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["chuna_training_banner_seen"] is True


async def test_GET_me_기본값은_모두_False(client, approved_doctor):
    _, headers = approved_doctor
    resp = await client.get("/api/auth/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["chuna_training_certified"] is False
    assert data["chuna_training_banner_seen"] is False


async def test_이수여부와_배너는_서로_독립적으로_저장됨(client, approved_doctor):
    """배너만 확인(seen=True)해도 이수여부(certified)는 그대로 False로 남아야 함."""
    _, headers = approved_doctor
    await client.patch("/api/auth/me", json={"chuna_training_banner_seen": True}, headers=headers)
    resp = await client.get("/api/auth/me", headers=headers)
    data = resp.json()
    assert data["chuna_training_banner_seen"] is True
    assert data["chuna_training_certified"] is False


# ── 2. notice_rules 순수 함수 단위 검증 ──────────────────────────────

def test_추나_있고_미이수면_ERROR():
    procedures = [{"fee_master_code": "40710", "name": "추나요법(단순)"}]
    doctor = {"chuna_training_certified": False}
    results = validate_notice_rules(procedures=procedures, doctor=doctor)
    errors = [r for r in results if r["rule_id"] == "NOTICE_CHUNA_TRAINING_REQUIRED"]
    assert len(errors) == 1
    assert errors[0]["severity"] == "ERROR"


def test_추나_있고_이수했으면_에러없음():
    procedures = [{"fee_master_code": "40710", "name": "추나요법(단순)"}]
    doctor = {"chuna_training_certified": True}
    results = validate_notice_rules(procedures=procedures, doctor=doctor)
    errors = [r for r in results if r["rule_id"] == "NOTICE_CHUNA_TRAINING_REQUIRED"]
    assert errors == []


def test_추나_없으면_미이수여도_에러없음():
    procedures = [{"fee_master_code": "40011", "name": "경혈침술(1부위)"}]  # 추나 아님
    doctor = {"chuna_training_certified": False}
    results = validate_notice_rules(procedures=procedures, doctor=doctor)
    errors = [r for r in results if r["rule_id"] == "NOTICE_CHUNA_TRAINING_REQUIRED"]
    assert errors == []


def test_doctor_None이면_검증_스킵():
    # doctor 정보를 못 넘기는 호출부(예: 구버전 호출)와의 하위호환 확인
    procedures = [{"fee_master_code": "40710", "name": "추나요법(단순)"}]
    results = validate_notice_rules(procedures=procedures, doctor=None)
    errors = [r for r in results if r["rule_id"] == "NOTICE_CHUNA_TRAINING_REQUIRED"]
    assert errors == []


# ── 3. create_claim() 통합 — 실제 청구 차단/통과 확인 ─────────────────

@pytest.fixture
async def chuna_fee_code(db):
    fee = FeeMaster(
        code="40710", name="추나요법(단순)", category="추나", unit_price=26330,
        is_insured=True, insured_health=True, insured_medical_aid=True, insured_veterans=False,
    )
    db.add(fee)
    await db.commit()
    return fee


async def _make_chuna_claim_inputs(db, hospital, doctor):
    patient = Patient(hospital_id=hospital.id, name="추나환자", gender="남", insurance_type="health")
    db.add(patient)
    await db.flush()
    record = MedicalRecord(
        patient_id=patient.id, doctor_id=doctor.id, hospital_id=hospital.id,
        kcd_code="M545", chart_structured="추나 시술", status="completed",
        recorded_at=datetime.now(timezone.utc),
    )
    db.add(record)
    await db.flush()
    db.add(MedicalRecordProcedure(
        medical_record_id=record.id, procedure_type="추나",
        amount=26330, is_non_benefit=False, fee_master_code="40710",
    ))
    await db.commit()
    return patient, record


async def test_미이수_한의사_추나_청구시_400_차단(db, approved_doctor, chuna_fee_code):
    doctor, _ = approved_doctor  # chuna_training_certified 기본값 False
    hospital = await db.get(Hospital, doctor.hospital_id)
    patient, record = await _make_chuna_claim_inputs(db, hospital, doctor)

    with pytest.raises(HTTPException) as exc_info:
        await create_claim(
            db=db, hospital_id=hospital.id, doctor_id=doctor.id, patient_id=patient.id,
            medical_record_ids=[record.id],
            claim_period_year=record.recorded_at.year, claim_period_month=record.recorded_at.month,
            visit_type="외래",
        )
    assert exc_info.value.status_code == 400
    error_ids = [e["rule_id"] for e in exc_info.value.detail["errors"]]
    assert "NOTICE_CHUNA_TRAINING_REQUIRED" in error_ids


async def test_이수한_한의사는_추나_청구_정상통과(db, approved_doctor, chuna_fee_code):
    doctor, _ = approved_doctor
    doctor.chuna_training_certified = True
    await db.commit()

    hospital = await db.get(Hospital, doctor.hospital_id)
    patient, record = await _make_chuna_claim_inputs(db, hospital, doctor)

    claim = await create_claim(
        db=db, hospital_id=hospital.id, doctor_id=doctor.id, patient_id=patient.id,
        medical_record_ids=[record.id],
        claim_period_year=record.recorded_at.year, claim_period_month=record.recorded_at.month,
        visit_type="외래",
    )
    assert claim.status == "draft"
    assert claim.patient_copay == 13165  # ceil(26330*0.50)


async def test_추나_없는_청구는_미이수여도_정상통과(db, approved_doctor):
    """추나 시술이 아예 없으면 사전교육 이수여부와 무관하게 청구 가능해야 함."""
    doctor, _ = approved_doctor  # 기본값 False (미이수)
    hospital = await db.get(Hospital, doctor.hospital_id)
    patient = Patient(hospital_id=hospital.id, name="일반환자", gender="남", insurance_type="health")
    db.add(patient)
    await db.flush()
    record = MedicalRecord(
        patient_id=patient.id, doctor_id=doctor.id, hospital_id=hospital.id,
        kcd_code="M545", chart_structured="일반 진료", status="completed",
        recorded_at=datetime.now(timezone.utc),
    )
    db.add(record)
    await db.flush()
    db.add(MedicalRecordProcedure(
        medical_record_id=record.id, procedure_type="진료",
        amount=10000, is_non_benefit=False, fee_master_code=None,
    ))
    await db.commit()

    claim = await create_claim(
        db=db, hospital_id=hospital.id, doctor_id=doctor.id, patient_id=patient.id,
        medical_record_ids=[record.id],
        claim_period_year=record.recorded_at.year, claim_period_month=record.recorded_at.month,
        visit_type="외래",
    )
    assert claim.patient_copay == 3000  # ceil(10000*0.30)
