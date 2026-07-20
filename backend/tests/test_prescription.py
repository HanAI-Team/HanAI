"""build_claim_prescription() — 처방전(별지9호서식) 출력용 데이터 조립 테스트."""

import pytest
from fastapi import HTTPException

from tests.test_edi_sample import 한의원_외래_사례, VISIT_DT  # noqa: F401

from app.billing.service import build_claim_prescription


async def test_처방전_기관_환자_의료인_정보_채워짐(db, 한의원_외래_사례):
    claim, hospital = 한의원_외래_사례
    p = await build_claim_prescription(db, hospital.id, claim.id)

    assert p.hospital_name == hospital.name
    assert p.institution_code == "12345678"
    assert p.patient_name == "한의외1"
    assert p.patient_birth_masked == "-"  # 사례 환자는 생년월일 미입력
    assert p.disease_names == ["M5459 요통, 상세불명의 부위"]
    assert p.license_type == "한의사"
    assert p.license_no
    assert p.issue_date == "2026-06-01"
    assert p.issue_no == "2026060001"


async def test_처방전_요양기관기호_없으면_생성차단(db, 한의원_외래_사례):
    """요양기관기호가 비어있으면 "-"로 얼버무리지 않고 생성 자체를 막는다."""
    claim, hospital = 한의원_외래_사례
    hospital.institution_code = None
    await db.commit()

    with pytest.raises(HTTPException) as exc_info:
        await build_claim_prescription(db, hospital.id, claim.id)
    assert exc_info.value.status_code == 400
