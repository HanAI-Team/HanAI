"""제출 처리(submit_claim)/반려 처리(reject_claim) 테스트 (2026-07-24 신설).

배경: 실제 제출은 요양기관정보마당 등 외부 채널에서 일어나 이 앱이 자동으로
알 방법이 없다. 그래서 직원이 포털에서 확인한 접수번호(제출 처리)/심사불능
사유코드(반려 처리)를 직접 입력하는 액션으로 draft→submitted, submitted→rejected
전이를 구현했다.
"""
import uuid

from sqlalchemy import select

from app.core.models import AuditLog, Claim, Patient


async def _make_claim(db, doctor, status: str) -> Claim:
    patient = Patient(hospital_id=doctor.hospital_id, name="제출테스트환자", insurance_type="health")
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
    )
    db.add(claim)
    await db.commit()
    await db.refresh(claim)
    return claim


async def test_draft_상태에서_제출처리하면_submitted로_전이(client, db, approved_doctor):
    doctor, headers = approved_doctor
    claim = await _make_claim(db, doctor, status="draft")

    resp = await client.post(
        f"/api/billing/claims/{claim.id}/submit",
        headers=headers,
        json={"receipt_no": 1234567},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "submitted"
    assert data["receipt_no"] == 1234567
    assert data["submitted_at"] is not None

    await db.refresh(claim)
    assert claim.status == "submitted"
    assert claim.receipt_no == 1234567
    assert claim.submitted_at is not None


async def test_draft가_아니면_제출처리_거부(client, db, approved_doctor):
    doctor, headers = approved_doctor
    claim = await _make_claim(db, doctor, status="submitted")

    resp = await client.post(
        f"/api/billing/claims/{claim.id}/submit",
        headers=headers,
        json={"receipt_no": 1234567},
    )
    assert resp.status_code == 409


async def test_제출처리시_감사로그_기록됨(client, db, approved_doctor):
    doctor, headers = approved_doctor
    claim = await _make_claim(db, doctor, status="draft")

    await client.post(
        f"/api/billing/claims/{claim.id}/submit",
        headers=headers,
        json={"receipt_no": 1234567},
    )

    result = await db.execute(
        select(AuditLog).where(AuditLog.table_name == "claims", AuditLog.record_id == str(claim.id))
    )
    logs = result.scalars().all()
    assert len(logs) == 1
    assert logs[0].action == "UPDATE"
    assert logs[0].actor_id == doctor.id
    assert "draft" in logs[0].detail and "submitted" in logs[0].detail


async def test_submitted_상태에서_반려처리하면_rejected로_전이(client, db, approved_doctor):
    doctor, headers = approved_doctor
    claim = await _make_claim(db, doctor, status="submitted")

    resp = await client.post(
        f"/api/billing/claims/{claim.id}/reject",
        headers=headers,
        json={"rejection_reason_code": "12"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "rejected"
    assert data["rejection_reason_code"] == "12"

    await db.refresh(claim)
    assert claim.status == "rejected"
    assert claim.rejection_reason_code == "12"


async def test_submitted가_아니면_반려처리_거부(client, db, approved_doctor):
    doctor, headers = approved_doctor
    claim = await _make_claim(db, doctor, status="draft")

    resp = await client.post(
        f"/api/billing/claims/{claim.id}/reject",
        headers=headers,
        json={"rejection_reason_code": "12"},
    )
    assert resp.status_code == 409


async def test_반려처리시_감사로그_기록됨(client, db, approved_doctor):
    doctor, headers = approved_doctor
    claim = await _make_claim(db, doctor, status="submitted")

    await client.post(
        f"/api/billing/claims/{claim.id}/reject",
        headers=headers,
        json={"rejection_reason_code": "12"},
    )

    result = await db.execute(
        select(AuditLog).where(AuditLog.table_name == "claims", AuditLog.record_id == str(claim.id))
    )
    logs = result.scalars().all()
    assert len(logs) == 1
    assert logs[0].action == "UPDATE"
    assert "submitted" in logs[0].detail and "rejected" in logs[0].detail


async def test_다른_병원_청구서는_제출처리_불가(client, db, approved_doctor):
    _, headers = approved_doctor
    other_hospital_claim_patient = Patient(hospital_id=uuid.uuid4(), name="다른병원환자", insurance_type="health")
    db.add(other_hospital_claim_patient)
    await db.flush()
    other_doctor_id = uuid.uuid4()
    claim = Claim(
        id=uuid.uuid4(), patient_id=other_hospital_claim_patient.id, doctor_id=other_doctor_id,
        hospital_id=other_hospital_claim_patient.hospital_id,
        claim_period_year=2026, claim_period_month=6, status="draft",
    )
    db.add(claim)
    await db.commit()

    resp = await client.post(
        f"/api/billing/claims/{claim.id}/submit",
        headers=headers,
        json={"receipt_no": 1234567},
    )
    assert resp.status_code == 404
