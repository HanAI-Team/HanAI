"""추나요법 관련 create_claim() 통합 테스트 (2026-07-07 신규, 2026-07-08 수정).

기존 test_chuna_copay_split.py / test_chuna_notice_rules.py는 순수 함수만
검증했고, service.create_claim() 안의 실제 DB 쿼리(_count_annual_chuna_sessions,
_count_daily_chuna_patients)는 한 번도 실행된 적이 없었다 (기존 테스트 스위트
전체를 돌려도 추나 코드가 포함된 청구가 하나도 없었음). 이 파일은 그 갭을
메운다.

2026-07-08 수정:
  - Doctor.chuna_training_certified 필드 신설(사전교육 이수 검증 기능 추가)로
    인해, 이 파일의 테스트들이 만드는 기본 의사(approved_doctor fixture)가
    미이수(False) 상태라 전부 400으로 막히던 문제 수정 — 각 테스트에서
    doctor.chuna_training_certified = True로 명시적으로 이수 처리 후 진행.
  - Claim.special_case_needs_review(Boolean) → special_case_review_reason
    (String, nullable)로 필드명 자체가 바뀐 것 반영 (review_reason 브랜치,
    #376 develop 머지 반영).
"""

from datetime import date, datetime, timedelta, timezone

import pytest

from app.billing.service import create_claim
from app.core.models import Hospital, MedicalRecord, MedicalRecordProcedure, Patient, FeeMaster

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def chuna_fee_codes(db):
    """추나 4개 코드 FeeMaster 픽스처 (MedicalRecordProcedure.fee_master_code FK 충족용)."""
    codes = [
        FeeMaster(code="40710", name="추나요법(단순)", category="추나", unit_price=26330,
                  is_insured=True, insured_health=True, insured_medical_aid=True, insured_veterans=False),
        FeeMaster(code="40720", name="추나요법(복잡)", category="추나", unit_price=44450,
                  is_insured=True, insured_health=True, insured_medical_aid=True, insured_veterans=False),
        FeeMaster(code="40721", name="추나요법(복잡-80%)", category="추나", unit_price=44450,
                  is_insured=True, insured_health=True, insured_medical_aid=True, insured_veterans=False),
        FeeMaster(code="40730", name="추나요법(특수-탈구)", category="추나", unit_price=68140,
                  is_insured=True, insured_health=True, insured_medical_aid=True, insured_veterans=False),
    ]
    db.add_all(codes)
    await db.commit()
    return codes


async def _certify_chuna_training(db, doctor) -> None:
    """이 파일의 테스트들은 추나 요율/한도 로직 검증이 목적이라, 사전교육
    이수 검증(별도 기능, test_chuna_training_certification.py에서 전담 검증)
    때문에 막히지 않도록 미리 이수 처리해준다."""
    doctor.chuna_training_certified = True
    await db.commit()


async def _make_patient(db, hospital, name="추나환자") -> Patient:
    patient = Patient(hospital_id=hospital.id, name=name, gender="남", insurance_type="health")
    db.add(patient)
    await db.flush()
    return patient


async def _make_chuna_record(db, hospital, doctor, patient, code, amount, recorded_at, kcd="M545"):
    """추나 시술 1건이 포함된 MedicalRecord + Procedure 생성 (아직 claim에 연결 안 됨)."""
    record = MedicalRecord(
        patient_id=patient.id, doctor_id=doctor.id, hospital_id=hospital.id,
        kcd_code=kcd, chart_structured="추나 시술", status="completed",
        recorded_at=recorded_at,
    )
    db.add(record)
    await db.flush()
    db.add(MedicalRecordProcedure(
        medical_record_id=record.id, procedure_type="추나",
        amount=amount, is_non_benefit=False, fee_master_code=code,
    ))
    await db.flush()
    return record


async def test_추나_50_80_요율_실제_DB_계산(db, approved_doctor, chuna_fee_codes):
    """40710(50%)+40721(80%) 혼합 청구 시 실제 청구금액이 분리 계산되는지 확인."""
    doctor, _ = approved_doctor
    await _certify_chuna_training(db, doctor)
    hospital = await db.get(Hospital, doctor.hospital_id)
    patient = await _make_patient(db, hospital)

    now = datetime.now(timezone.utc)
    record1 = await _make_chuna_record(db, hospital, doctor, patient, "40710", 26330, now)
    record2 = await _make_chuna_record(db, hospital, doctor, patient, "40721", 44450, now)
    await db.commit()

    claim = await create_claim(
        db=db, hospital_id=hospital.id, doctor_id=doctor.id, patient_id=patient.id,
        medical_record_ids=[record1.id, record2.id],
        claim_period_year=now.year, claim_period_month=now.month, visit_type="외래",
    )

    expected = 13165 + 35560  # ceil(26330*0.5) + ceil(44450*0.8)
    assert claim.patient_copay == expected
    assert claim.total_amount == 26330 + 44450


async def test_추나_연간_20회_이하는_review_reason_없음(db, approved_doctor, chuna_fee_codes):
    doctor, _ = approved_doctor
    await _certify_chuna_training(db, doctor)
    hospital = await db.get(Hospital, doctor.hospital_id)
    patient = await _make_patient(db, hospital)

    this_year = date.today().year
    base_dt = datetime(this_year, 3, 1, tzinfo=timezone.utc)

    # 이미 19회 시행된 상태로 만들고, 이번 청구 1건을 추가 = 총 20회 (한도 이내)
    for i in range(19):
        await _make_chuna_record(
            db, hospital, doctor, patient, "40710", 26330,
            base_dt + timedelta(days=i),
        )
    await db.commit()

    new_record = await _make_chuna_record(
        db, hospital, doctor, patient, "40710", 26330, base_dt + timedelta(days=100),
    )
    await db.commit()

    claim = await create_claim(
        db=db, hospital_id=hospital.id, doctor_id=doctor.id, patient_id=patient.id,
        medical_record_ids=[new_record.id],
        claim_period_year=this_year, claim_period_month=6, visit_type="외래",
    )
    assert claim.special_case_review_reason is None


async def test_추나_연간_20회_초과시_review_reason_뜸(db, approved_doctor, chuna_fee_codes):
    doctor, _ = approved_doctor
    await _certify_chuna_training(db, doctor)
    hospital = await db.get(Hospital, doctor.hospital_id)
    patient = await _make_patient(db, hospital)

    this_year = date.today().year
    base_dt = datetime(this_year, 3, 1, tzinfo=timezone.utc)

    # 이미 20회 시행된 상태로 만들고, 이번 청구 1건을 추가 = 총 21회 (한도 초과)
    for i in range(20):
        await _make_chuna_record(
            db, hospital, doctor, patient, "40710", 26330,
            base_dt + timedelta(days=i),
        )
    await db.commit()

    new_record = await _make_chuna_record(
        db, hospital, doctor, patient, "40710", 26330, base_dt + timedelta(days=100),
    )
    await db.commit()

    claim = await create_claim(
        db=db, hospital_id=hospital.id, doctor_id=doctor.id, patient_id=patient.id,
        medical_record_ids=[new_record.id],
        claim_period_year=this_year, claim_period_month=6, visit_type="외래",
    )
    assert claim.special_case_review_reason is not None
    assert "chuna_limit_exceeded" in claim.special_case_review_reason


async def test_추나_1일_18명_초과시_review_reason_뜸(db, approved_doctor, chuna_fee_codes):
    """같은 한의사가 같은 날 18명을 초과해 추나를 시행한 경우 review_reason에 노출."""
    doctor, _ = approved_doctor
    await _certify_chuna_training(db, doctor)
    hospital = await db.get(Hospital, doctor.hospital_id)

    target_date = date.today().replace(month=6, day=15)
    target_dt = datetime.combine(target_date, datetime.min.time(), tzinfo=timezone.utc)

    # 이미 18명의 다른 환자에게 같은 날 추나 시행
    for i in range(18):
        other_patient = await _make_patient(db, hospital, name=f"환자{i}")
        await _make_chuna_record(db, hospital, doctor, other_patient, "40710", 26330, target_dt)
    await db.commit()

    # 19번째 환자 — 이 청구까지 합치면 당일 19명째
    last_patient = await _make_patient(db, hospital, name="19번째환자")
    new_record = await _make_chuna_record(db, hospital, doctor, last_patient, "40710", 26330, target_dt)
    await db.commit()

    claim = await create_claim(
        db=db, hospital_id=hospital.id, doctor_id=doctor.id, patient_id=last_patient.id,
        medical_record_ids=[new_record.id],
        claim_period_year=target_date.year, claim_period_month=target_date.month, visit_type="외래",
    )
    assert claim.special_case_review_reason is not None
    assert "chuna_limit_exceeded" in claim.special_case_review_reason


async def test_추나_없는_청구는_DB_카운트_쿼리_아예_안_타고_정상동작(db, approved_doctor):
    """추나 항목이 없으면 chuna_annual_count/chuna_daily_doctor_count가 None으로 유지되고,
    기존 동작(일반 진료 30%)이 그대로 유지되는지 회귀 확인.

    이 테스트는 의도적으로 이수 처리를 안 함 — 추나가 없는 청구는 사전교육
    여부와 무관하게 정상 통과해야 한다는 걸 같이 확인하기 위함."""
    doctor, _ = approved_doctor
    hospital = await db.get(Hospital, doctor.hospital_id)
    patient = await _make_patient(db, hospital)

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
        claim_period_year=date.today().year, claim_period_month=date.today().month, visit_type="외래",
    )
    assert claim.patient_copay == 3000  # ceil(10000*0.30), 산정특례/추나 없는 일반 케이스
    assert claim.special_case_review_reason is None
