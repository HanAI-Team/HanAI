"""
notice_rules.py 검증 로직 테스트.

배경: create_claim()에서 validate_notice_rules() 호출 시 키워드 인자명이
    (records=, claim_period_year=, claim_period_month=) 였으나 실제 함수
    시그니처는 (_records=, _claim_period_year=, _claim_period_month=) 라서
    TypeError가 발생해 청구 생성 자체가 막혔던 버그가 있었음 (수정 완료).

이 파일은 다음을 검증한다:
  1. 정상적인 진료기록으로 create_claim() 호출 시 TypeError 없이 청구가 생성되는지
     (notice_rules 호출부 버그의 핵심 회귀 테스트)
  2. notice_rules.py가 실제로 차단(ERROR)해야 하는 케이스에서 400을 반환하는지
     (보훈국비환자 MT038/JT019 특정내역 누락)
"""

import pytest
from fastapi import HTTPException

from app.billing.service import create_claim
from app.core.models import Hospital, MedicalRecord, Patient

pytestmark = pytest.mark.asyncio


async def test_create_claim_정상케이스_TypeError_없이_생성됨(
    db, approved_doctor, kcd_codes
):
    """
    회귀 테스트: notice_rules 호출부 키워드 인자명 버그 수정 검증.

    B001(장티푸스, is_notifiable=False, sex_restriction=None)처럼 특별한
    검증 규칙에 걸리지 않는 평범한 상병코드로 create_claim()을 호출했을 때
    TypeError 없이 Claim이 정상 생성되어야 한다.

    ※ visit_type은 VisitType enum(app/billing/copayment.py)이 "외래"/"입원"
      한글 값을 쓰므로 명시적으로 지정한다. create_claim()의 기본값
      "outpatient"는 VisitType과 맞지 않아 그대로 두면 ValueError가 나므로
      이 테스트에서는 회귀 대상(notice_rules 버그)과 무관한 실패를 피하기
      위해 "외래"를 직접 전달한다.
    """
    doctor, _ = approved_doctor
    hospital = await db.get(Hospital, doctor.hospital_id)

    patient = Patient(
        hospital_id=hospital.id,
        name="정상환자",
        gender="남",
        insurance_type="health",
    )
    db.add(patient)
    await db.flush()

    record = MedicalRecord(
        patient_id=patient.id,
        doctor_id=doctor.id,
        hospital_id=hospital.id,
        kcd_code="B001",
        chart_structured="장티푸스 의심 소견 없음, 일반 진료",
        status="completed",
    )
    db.add(record)
    await db.commit()

    # TypeError가 발생하면 여기서 그대로 터짐 — pytest가 실패로 잡아준다.
    claim = await create_claim(
        db=db,
        hospital_id=hospital.id,
        doctor_id=doctor.id,
        patient_id=patient.id,
        medical_record_ids=[record.id],
        claim_period_year=2026,
        claim_period_month=6,
        visit_type="외래",
    )

    assert claim is not None
    assert claim.status == "draft"
    assert claim.patient_id == patient.id


async def test_create_claim_보훈국비환자_MT038_JT019_누락시_차단(
    db, approved_doctor, kcd_codes
):
    """
    notice_rules.py 규칙 검증: 보훈국비환자는 MT038/JT019 특정내역 기재가
    필수이며, 현재 서비스 로직에는 이를 자동으로 채우는 부분이 없으므로
    항상 ERROR로 차단되어야 한다 (제2012-117호).

    ※ notice_rules.py는 검사 대상 insurance_type을
      {"BOHUN", "BOHUN_PUBLIC", "보훈", "보훈국비", "보험국비"} 로 판정하는데,
      service.py의 _INSURANCE_MAP은 보훈을 "veterans"/"7"로 매핑한다.
      두 모듈의 문자열 체계가 달라 실제 DB에 insurance_type="veterans"로
      저장된 보훈 환자는 이 차단 로직에 전혀 걸리지 않을 수 있음
      (별도 확인 필요 — 이 테스트는 notice_rules.py 자체 로직만 검증하기
      위해 "BOHUN"을 직접 사용한다).
    """
    doctor, _ = approved_doctor
    hospital = await db.get(Hospital, doctor.hospital_id)

    patient = Patient(
        hospital_id=hospital.id,
        name="보훈환자",
        gender="남",
        insurance_type="BOHUN",  # notice_rules.py가 검사하는 보훈국비 표기
    )
    db.add(patient)
    await db.flush()

    record = MedicalRecord(
        patient_id=patient.id,
        doctor_id=doctor.id,
        hospital_id=hospital.id,
        kcd_code="B001",
        chart_structured="일반 진료",
        status="completed",
    )
    db.add(record)
    await db.commit()

    with pytest.raises(HTTPException) as exc_info:
        await create_claim(
            db=db,
            hospital_id=hospital.id,
            doctor_id=doctor.id,
            patient_id=patient.id,
            medical_record_ids=[record.id],
            claim_period_year=2026,
            claim_period_month=6,
            visit_type="외래",
        )

    assert exc_info.value.status_code == 400
    detail = exc_info.value.detail
    error_codes = [e["code"] for e in detail["errors"]]
    assert "MT038" in error_codes
    assert "JT019" in error_codes
