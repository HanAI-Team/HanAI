"""심사결과 CSV 업로드 → Claim.status 전이 테스트 (2026-07-24 신설).

배경: create_review_results_from_csv()는 지금까지 ClaimReviewResult 레코드만
만들 뿐 Claim.status는 전혀 건드리지 않아서, 화면의 제출완료/승인/반려 필터가
정상 사용 흐름으로는 절대 채워지지 않았다. 이 파일은 CSV 업로드 시점에
_transition_claim_status_from_review()가 실제로 status를 approved로 전이시키는지,
그리고 그 판단 기준("인정"/"삭감"→approved, "보류"→전이 없음)이 맞는지 확인한다.
"""
import uuid

from sqlalchemy import select

from app.billing.service import create_review_results_from_csv
from app.core.models import AuditLog, Claim, ClaimReviewResult, Patient


def _make_csv(rows: list[dict]) -> bytes:
    header = "접수번호,심사구분,결과코드,청구금액,인정금액,삭감금액,삭감사유,심사일자"
    lines = [header]
    for r in rows:
        lines.append(
            f"{r['접수번호']},{r['심사구분']},{r['결과코드']},"
            f"{r.get('청구금액', 100000)},{r.get('인정금액', 100000)},{r.get('삭감금액', 0)},"
            f"{r.get('삭감사유', '')},{r['심사일자']}"
        )
    return ("\n".join(lines)).encode("utf-8-sig")


async def _make_claim(db, doctor, receipt_no: int, status: str = "submitted") -> Claim:
    patient = Patient(hospital_id=doctor.hospital_id, name="심사결과환자", insurance_type="health")
    db.add(patient)
    await db.flush()
    claim = Claim(
        id=uuid.uuid4(),
        patient_id=patient.id,
        doctor_id=doctor.id,
        hospital_id=doctor.hospital_id,
        claim_period_year=2026,
        claim_period_month=6,
        total_amount=100000,
        patient_copay=30000,
        claim_amount=70000,
        status=status,
        receipt_no=receipt_no,
    )
    db.add(claim)
    await db.commit()
    await db.refresh(claim)
    return claim


async def test_인정_결과면_청구서_approved로_전이(db, approved_doctor):
    doctor, _ = approved_doctor
    claim = await _make_claim(db, doctor, receipt_no=1001)

    csv = _make_csv([{"접수번호": 1001, "심사구분": "원심사", "결과코드": "인정", "심사일자": "2026-06-15"}])
    inserted, skipped = await create_review_results_from_csv(db, doctor.hospital_id, csv, actor_id=doctor.id)

    assert inserted == 1
    assert skipped == 0
    await db.refresh(claim)
    assert claim.status == "approved"


async def test_삭감_결과도_approved로_전이(db, approved_doctor):
    """삭감은 청구 금액이 깎였을 뿐 청구 자체는 심사가 끝난 것이라 반려와 다르다."""
    doctor, _ = approved_doctor
    claim = await _make_claim(db, doctor, receipt_no=1002)

    csv = _make_csv([{"접수번호": 1002, "심사구분": "원심사", "결과코드": "삭감", "삭감금액": 5000, "심사일자": "2026-06-15"}])
    await create_review_results_from_csv(db, doctor.hospital_id, csv, actor_id=doctor.id)

    await db.refresh(claim)
    assert claim.status == "approved"


async def test_보류_결과는_상태_유지(db, approved_doctor):
    doctor, _ = approved_doctor
    claim = await _make_claim(db, doctor, receipt_no=1003, status="submitted")

    csv = _make_csv([{"접수번호": 1003, "심사구분": "원심사", "결과코드": "보류", "심사일자": "2026-06-15"}])
    await create_review_results_from_csv(db, doctor.hospital_id, csv, actor_id=doctor.id)

    await db.refresh(claim)
    assert claim.status == "submitted"  # 전이 없음


async def test_draft_상태여도_인정결과면_approved로_전이(db, approved_doctor):
    """draft→submitted 트리거는 이번 스코프 밖이라, 실제로는 CSV 도착 시점에
    아직 draft인 청구서도 많다. 이 경우에도 approved로 전이되어야
    (submitted를 거치지 않아도) 기능 자체가 무력화되지 않는다."""
    doctor, _ = approved_doctor
    claim = await _make_claim(db, doctor, receipt_no=1004, status="draft")

    csv = _make_csv([{"접수번호": 1004, "심사구분": "원심사", "결과코드": "인정", "심사일자": "2026-06-15"}])
    await create_review_results_from_csv(db, doctor.hospital_id, csv, actor_id=doctor.id)

    await db.refresh(claim)
    assert claim.status == "approved"


async def test_매칭안되는_접수번호는_상태변화_없음(db, approved_doctor):
    doctor, _ = approved_doctor
    claim = await _make_claim(db, doctor, receipt_no=1005, status="submitted")

    csv = _make_csv([{"접수번호": 9999999, "심사구분": "원심사", "결과코드": "인정", "심사일자": "2026-06-15"}])
    inserted, skipped = await create_review_results_from_csv(db, doctor.hospital_id, csv, actor_id=doctor.id)

    assert inserted == 1
    await db.refresh(claim)
    assert claim.status == "submitted"  # 무관한 청구서는 영향 없음

    result = await db.execute(select(ClaimReviewResult).where(ClaimReviewResult.receipt_number == "9999999"))
    row = result.scalar_one()
    assert row.claim_id is None  # 매칭 실패 시 null로 남아야 함


async def test_전이시_감사로그_기록됨(db, approved_doctor):
    doctor, _ = approved_doctor
    claim = await _make_claim(db, doctor, receipt_no=1006)

    csv = _make_csv([{"접수번호": 1006, "심사구분": "원심사", "결과코드": "인정", "심사일자": "2026-06-15"}])
    await create_review_results_from_csv(db, doctor.hospital_id, csv, actor_id=doctor.id)

    result = await db.execute(
        select(AuditLog).where(AuditLog.table_name == "claims", AuditLog.record_id == str(claim.id))
    )
    logs = result.scalars().all()
    assert len(logs) == 1
    assert logs[0].action == "UPDATE"
    assert logs[0].actor_id == doctor.id
    assert "submitted" in logs[0].detail and "approved" in logs[0].detail


async def test_이미_approved인_청구에_재심사_결과_다시와도_감사로그_중복없음(db, approved_doctor):
    """이의신청·재심사로 동일한 결과(인정)가 다시 CSV로 들어와도 이미 approved라면
    아무 것도 바뀌지 않아야 하고(불필요한 감사로그도 남기지 않음)."""
    doctor, _ = approved_doctor
    claim = await _make_claim(db, doctor, receipt_no=1007, status="approved")

    csv = _make_csv([{"접수번호": 1007, "심사구분": "재심사", "결과코드": "인정", "심사일자": "2026-06-20"}])
    await create_review_results_from_csv(db, doctor.hospital_id, csv, actor_id=doctor.id)

    await db.refresh(claim)
    assert claim.status == "approved"

    result = await db.execute(
        select(AuditLog).where(AuditLog.table_name == "claims", AuditLog.record_id == str(claim.id))
    )
    assert len(result.scalars().all()) == 0


async def test_original_receipt_no만_있고_receipt_no_없으면_매칭_안됨(db, approved_doctor):
    """2026-07-24: 매칭 기준을 original_receipt_no→receipt_no로 전환했다.
    보완·추가청구 참조용 original_receipt_no만 있고 receipt_no(제출 처리 시
    기재하는 이 청구서 자체의 접수번호)가 없는 청구서는 더 이상 매칭되지
    않아야 한다(전환이 실제로 적용됐는지 확인)."""
    doctor, _ = approved_doctor
    patient = Patient(hospital_id=doctor.hospital_id, name="심사결과환자", insurance_type="health")
    db.add(patient)
    await db.flush()
    claim = Claim(
        id=uuid.uuid4(), patient_id=patient.id, doctor_id=doctor.id, hospital_id=doctor.hospital_id,
        claim_period_year=2026, claim_period_month=6, status="submitted",
        original_receipt_no=2001,  # receipt_no는 의도적으로 비움
    )
    db.add(claim)
    await db.commit()

    csv = _make_csv([{"접수번호": 2001, "심사구분": "원심사", "결과코드": "인정", "심사일자": "2026-06-15"}])
    await create_review_results_from_csv(db, doctor.hospital_id, csv, actor_id=doctor.id)

    await db.refresh(claim)
    assert claim.status == "submitted"  # 매칭 안 됨 → 전이도 없음


async def test_CSV_업로드_엔드포인트_통합_테스트(client, db, approved_doctor):
    """라우터(멀티파트 업로드)까지 포함한 전체 경로 확인."""
    doctor, headers = approved_doctor
    claim = await _make_claim(db, doctor, receipt_no=1008)

    csv = _make_csv([{"접수번호": 1008, "심사구분": "원심사", "결과코드": "인정", "심사일자": "2026-06-15"}])
    resp = await client.post(
        "/api/billing/claims/review-results/upload",
        headers=headers,
        files={"file": ("review.csv", csv, "text/csv")},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["inserted"] == 1

    await db.refresh(claim)
    assert claim.status == "approved"
