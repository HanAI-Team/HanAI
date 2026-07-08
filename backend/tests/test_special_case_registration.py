from datetime import date, timedelta
from decimal import Decimal

from app.billing.service import (
    SpecialCaseResolution,
    _SPECIAL_CASE_COPAY_RATE,
    _UNKNOWN_SPECIAL_CODE_RATE,
    create_claim,
    resolve_active_special_code,
)
from app.core.models import Hospital, MedicalRecord, MedicalRecordProcedure, Patient, SpecialCaseRegistration

# pytest.ini/pyproject.toml에 asyncio_mode=auto로 설정돼 있어 개별 async def 테스트는
# 별도 마크 없이도 자동 인식된다. 예전엔 여기 `pytestmark = pytest.mark.asyncio`가
# 있었는데, 이번에 추가한 동기(sync) 테스트(test_SPECIAL_CASE_COPAY_RATE_...)에도
# 모듈 전체 마크가 적용되면서 "asyncio로 마크됐는데 async 함수가 아니다"는 워닝이
# 떠서 제거함 — auto 모드에선 애초에 없어도 되는 마크였음.


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


def test_SPECIAL_CASE_COPAY_RATE_V221_V800_확정값_V027_삭제():
    """2026-07-07 재검증 반영 확인 (law.go.kr 별표4/별표4의2 + HIRA 별표6 원문 대조).

    - V221: "중증화상"이 아니라 별표4 소속 레쉬-니한증후군(E79.1) → 10%
    - V800: 면제(0%)가 아니라 V810과 동일하게 10% (별표4의2 구분6, 일수제한 없음)
    - V027: "미등록 암환자" 코드였으나 HIRA 고시 제2020-191호(2020-09-01 시행)로
      공식 폐지됨 → 테이블에서 완전히 제거되어 더 이상 키로 존재하지 않아야 함

    이 테스트는 딕셔너리 값을 직접 확인하므로, resolve_active_special_code()의
    결과(special_code/needs_review)만으로는 잡아내지 못하는 "값 자체가 틀렸는데
    다른 이유로 우연히 테스트가 통과하는" 상황을 막아준다.
    """
    assert _SPECIAL_CASE_COPAY_RATE["V221"] == (Decimal("0.10"), False)
    assert _SPECIAL_CASE_COPAY_RATE["V800"] == (Decimal("0.10"), False)
    assert "V027" not in _SPECIAL_CASE_COPAY_RATE


async def test_등록없으면_None(db):
    hospital = await _make_hospital(db)
    patient = await _make_patient(db, hospital)
    await db.commit()

    result = await resolve_active_special_code(db, patient.id)
    assert result == SpecialCaseResolution(special_code=None, review_reason=None)


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
    assert result.review_reason is None


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
    assert result.review_reason is None


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
    assert result.review_reason is None


async def test_낮은본인부담률_우선선택(db):
    """V191(뇌혈관, 5%)과 V800(중증치매, 10%)이 동시 활성이면
    본인부담률이 낮은 V191이 선택된다.

    2026-07-07 정정: 원래 이 테스트는 "V027(희귀난치, 10%)"을 짝으로 썼으나,
    V027은 HIRA 고시 제2020-191호(2020-09-01 시행)로 공식 폐지된 코드라
    "확정 10%"라는 설명 자체가 틀렸음. 여전히 유효한 V800(10%)으로 교체.
    """
    hospital = await _make_hospital(db)
    patient = await _make_patient(db, hospital)
    db.add_all([
        SpecialCaseRegistration(
            patient_id=patient.id, special_code="V191", category="뇌혈관",  # 확정 5%
            registered_at=date(2026, 1, 1),
        ),
        SpecialCaseRegistration(
            patient_id=patient.id, special_code="V800", category="중증치매",  # 확정 10%
            registered_at=date(2026, 1, 1),
        ),
    ])
    await db.commit()

    result = await resolve_active_special_code(db, patient.id)
    assert result.special_code == "V191"
    assert result.review_reason is None


async def test_V192_확정값_반환(db):
    """V192(심장, 5%)는 확정값으로 처리되어 needs_review=False."""
    hospital = await _make_hospital(db)
    patient = await _make_patient(db, hospital)
    db.add(SpecialCaseRegistration(
        patient_id=patient.id, special_code="V192", category="심장",
        registered_at=date(2026, 1, 1),
    ))
    await db.commit()

    result = await resolve_active_special_code(db, patient.id)
    assert result.special_code == "V192"
    assert result.review_reason is None


async def test_F006_단독등록시_확정_40퍼센트(db):
    """F006(신체기능저하군)은 단독 등록이면 확정값(40%)으로 처리되고 needs_review=False."""
    hospital = await _make_hospital(db)
    patient = await _make_patient(db, hospital)
    db.add(SpecialCaseRegistration(
        patient_id=patient.id, special_code="F006", category="신체기능저하군",
        registered_at=date(2026, 1, 1),
    ))
    await db.commit()

    result = await resolve_active_special_code(db, patient.id)
    assert result.special_code == "F006"
    assert result.review_reason is None


async def test_F006과_암_동시활성시_예외로_needs_review_강제(db):
    """F006 + 암(V193) 동시 활성 — 별도 규정 미구현 상태라 needs_review=True로 강제.
    (본인부담률만 보면 V193의 5%가 F006의 40%보다 낮아 V193이 선택되지만,
    F006 동시해당 예외 자체를 이번 스코프에서 구현하지 않았으므로 confident하게
    반환하면 안 된다.)"""
    hospital = await _make_hospital(db)
    patient = await _make_patient(db, hospital)
    db.add_all([
        SpecialCaseRegistration(
            patient_id=patient.id, special_code="F006", category="신체기능저하군",
            registered_at=date(2026, 1, 1),
        ),
        SpecialCaseRegistration(
            patient_id=patient.id, special_code="V193", category="암",
            registered_at=date(2026, 1, 1),
        ),
    ])
    await db.commit()

    result = await resolve_active_special_code(db, patient.id)
    assert result.special_code == "V193"  # 본인부담률만으로는 여전히 V193이 최저값
    assert result.review_reason == "f006_concurrent"   # 하지만 F006 동시해당 예외 때문에 확신할 수 없음


async def test_V221_레쉬니한증후군_10퍼센트_확정됨(db):
    """2026-07-07 정정: V221은 "중증화상 5%"가 아니라 별표4 소속
    레쉬-니한증후군(E79.1)이며 10%가 맞다. 이 테스트는 이름/설명뿐 아니라
    실제 요율(_SPECIAL_CASE_COPAY_RATE)까지 함께 확인해, "needs_review만
    확인하고 실제 숫자는 안 봐서 값이 틀려도 통과하던" 이전 버전의 허점을
    막는다.
    """
    hospital = await _make_hospital(db)
    patient = await _make_patient(db, hospital)
    db.add(SpecialCaseRegistration(
        patient_id=patient.id, special_code="V221", category="희귀질환",
        registered_at=date(2026, 1, 1),
    ))
    await db.commit()

    result = await resolve_active_special_code(db, patient.id)
    assert result.special_code == "V221"
    assert result.review_reason is None
    assert _SPECIAL_CASE_COPAY_RATE["V221"] == (Decimal("0.10"), False)


async def test_V810_사전승인번호_없으면_needs_review(db):
    """V810(중증치매 일반)은 공단 사전승인번호 없이 등록되면 needs_review=True."""
    hospital = await _make_hospital(db)
    patient = await _make_patient(db, hospital)
    db.add(SpecialCaseRegistration(
        patient_id=patient.id, special_code="V810", category="중증치매",
        registered_at=date(2026, 1, 1),
        prior_approval_number=None,
    ))
    await db.commit()

    result = await resolve_active_special_code(db, patient.id)
    assert result.special_code == "V810"
    assert result.review_reason == "v810_no_approval"


async def test_V810_사전승인번호_있으면_정상(db):
    """V810(중증치매 일반)에 사전승인번호가 있으면 needs_review=False."""
    hospital = await _make_hospital(db)
    patient = await _make_patient(db, hospital)
    db.add(SpecialCaseRegistration(
        patient_id=patient.id, special_code="V810", category="중증치매",
        registered_at=date(2026, 1, 1),
        prior_approval_number="1-26-00000001",
    ))
    await db.commit()

    result = await resolve_active_special_code(db, patient.id)
    assert result.special_code == "V810"
    assert result.review_reason is None
    assert result.prior_approval_number == "1-26-00000001"


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
    assert claim.special_case_review_reason is None


async def test_create_claim_V221_10퍼센트_실제금액_반영(db, approved_doctor, kcd_codes):
    """create_claim() 전체 경로로 V221(레쉬-니한증후군, 10%)이 5%가 아니라
    정확히 10%로 계산되는지 끝까지 확인한다 (resolve 단계만이 아니라 실제
    청구 금액까지 검증하는 회귀 방지용 테스트)."""
    doctor, _ = approved_doctor
    hospital = await db.get(Hospital, doctor.hospital_id)

    patient = Patient(hospital_id=hospital.id, name="희귀질환환자", gender="남", insurance_type="health")
    db.add(patient)
    await db.flush()

    db.add(SpecialCaseRegistration(
        patient_id=patient.id, special_code="V221", category="희귀질환",
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

    assert claim.patient_copay == 10000  # ceil(100000*0.10) — 5000(구 5%값)이면 회귀
    assert claim.special_case_review_reason is None


async def test_create_claim_확정된_뇌혈관코드는_플래그_노출_안됨(db, approved_doctor, kcd_codes):
    """V191(뇌혈관)은 확정 코드이므로 needs_review가 노출되지 않는다.

    2026-07-07 정정: 이 테스트는 원래 이름이 "확인필요 산정특례는 플래그가
    노출된다"였는데, 실제로는 확정 코드(V191)를 등록해놓고 needs_review=False를
    확인하는 내용이라 이름과 내용이 정반대였음. 이름을 실제 내용에 맞게
    고치고, "확인필요가 실제로 노출되는" 시나리오는 아래
    test_create_claim_미확인_특정기호는_needs_review_노출 로 별도 분리함.
    """
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

    assert claim.special_case_review_reason is None


async def test_create_claim_미확인_특정기호는_needs_review_노출(db, approved_doctor, kcd_codes):
    """DB에 폐지된/미확인 특정기호(V027)가 남아있는 경우, create_claim()이
    확정값인 척 조용히 계산하지 않고 needs_review=True를 노출해야 한다.

    V027은 HIRA 고시 제2020-191호로 폐지됐지만, 혹시 예전 데이터나 수기
    입력 실수로 DB에 남아있을 수 있는 상황을 가정한 회귀 방지 테스트.

    ⚠️ 2026-07-07 발견: needs_review=True는 제대로 뜨지만, 실제 청구금액
    (patient_copay)은 service.py의 _UNKNOWN_SPECIAL_CODE_RATE(19%)가 아니라
    copayment.py._special_rate()의 자체 fallback(10%)으로 계산된다.
    resolve_active_special_code()는 special_code 문자열만 반환하고, 그 문자열이
    다시 calculate_billing() → copayment.py._special_rate()로 넘어가면서 19%라는
    숫자 자체는 완전히 유실됨 — 두 파일의 fallback이 서로 다른 목적(순위 결정용
    19% vs 실제 금액 계산용 10%)으로 분리되어 있고 서로 연결돼 있지 않다.
    needs_review 플래그가 뜨니 사람이 재확인할 거라는 전제로 설계된 것일 수도
    있지만, 의도한 설계인지 재확인 필요 — 태균에게 확인 요청 예정.
    """
    doctor, _ = approved_doctor
    hospital = await db.get(Hospital, doctor.hospital_id)

    patient = Patient(hospital_id=hospital.id, name="레거시데이터환자", gender="남", insurance_type="health")
    db.add(patient)
    await db.flush()

    db.add(SpecialCaseRegistration(
        patient_id=patient.id, special_code="V027", category="희귀난치",
        registered_at=date(2020, 1, 1),
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

    # review_reason은 service.py의 _UNKNOWN_SPECIAL_CODE_RATE(19%) 기준으로 채워짐.
    assert claim.special_case_review_reason == "unconfirmed_rate"
    # 하지만 실제 금액은 copayment.py._special_rate()의 독립적인 fallback(10%)으로 계산됨.
    # 19%가 아니라 10%가 나오는 게 "현재 코드의 실제 동작"이며, 이 값이 맞는 설계인지는
    # 별도 확인이 필요하다 (위 docstring 참고).
    assert claim.patient_copay == 10000  # ceil(100000*0.10) — copayment.py fallback


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
    """patient_id 없이 body의 special_code를 직접 쓰는 정상 경로 — 유효한
    코드(V193)로 확인한다.

    2026-07-07 정정: 원래 이 테스트는 예시 코드로 V027을 썼는데, V027은
    HIRA 고시 제2020-191호로 폐지된 코드라 "정상 사용 예시"로 부적절함.
    폐지된 코드가 fallback을 타는 동작 자체는 아래
    test_calculate_엔드포인트_폐지된코드_fallback_적용 으로 분리해서 명시적으로
    검증한다.
    """
    _, headers = approved_doctor

    resp = await client.post(
        "/api/billing/calculate",
        json={
            "insurance_type": "4",
            "visit_type": "외래",
            "benefit_total": 100000,
            "special_code": "V193",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["special_code"] == "V193"
    assert data["needs_review"] is False
    assert data["copayment"] == 5000  # ceil(100000*0.05)


async def test_calculate_엔드포인트_폐지된코드_fallback_적용(client, approved_doctor):
    """V027(HIRA 고시 제2020-191호로 폐지)을 body special_code로 직접 넘기면
    copayment.py._special_rate의 fallback(10%)이 적용된다.

    이 엔드포인트는 resolve_active_special_code()를 거치지 않고
    calculate_billing()을 직접 호출하는 경로다. 이 경로의 needs_review는
    (patient_id 기반 DB 조회 없이) 항상 False로 내려오는 것으로 보이므로 —
    즉 "값이 틀렸는데도 확인이 필요하다는 신호가 없는" 상태 — 이 테스트는
    "폐지된 코드를 넣어도 서버가 죽지 않고 fallback으로 조용히 넘어간다"는
    것만 확인하는 안전망이다. 실제 서비스에서 이 코드가 쓰일 일이 없어야
    하며, patient_id를 넘기는 경로(resolve_active_special_code 경유)에서는
    위 test_create_claim_미확인_특정기호는_needs_review_노출 처럼 제대로
    needs_review=True로 잡힌다 — 그 경로가 훨씬 안전하다.
    """
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
    assert data["needs_review"] is False  # 이 경로엔 needs_review 판단 로직 자체가 없음 — 알고 있는 한계
    assert data["copayment"] == 10000  # ceil(100000*0.10), fallback
