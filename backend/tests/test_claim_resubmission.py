"""보완·추가청구 PATCH /claims/{id}/resubmission 테스트."""
import uuid

import pytest_asyncio
from sqlalchemy import select

from app.core.models import Claim, ClaimResubmissionHistory, Patient


@pytest_asyncio.fixture
async def rejected_claim(db, approved_doctor):
    doctor, headers = approved_doctor
    patient = Patient(hospital_id=doctor.hospital_id, name="청구환자1", insurance_type="health")
    db.add(patient)
    await db.flush()

    claim = Claim(
        id=uuid.uuid4(),
        patient_id=patient.id,
        doctor_id=doctor.id,
        hospital_id=doctor.hospital_id,
        claim_period_year=2026,
        claim_period_month=6,
        total_amount=10000,
        patient_copay=3000,
        claim_amount=7000,
        status="rejected",
    )
    db.add(claim)
    await db.commit()
    return claim, headers


async def test_보완청구_정상처리(client, rejected_claim):
    claim, headers = rejected_claim
    resp = await client.patch(
        f"/api/billing/claims/{claim.id}/resubmission",
        headers=headers,
        json={
            "claim_type": "supplement",
            "original_receipt_no": 1234567,
            "original_record_serial": 5,
            "rejection_reason_code": "12",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["claim_type"] == "supplement"
    assert body["original_receipt_no"] == 1234567
    assert body["original_record_serial"] == 5
    assert body["rejection_reason_code"] == "12"
    assert body["status"] == "rejected"  # 상태는 그대로 유지


async def test_추가청구는_사유코드_무시(client, rejected_claim):
    claim, headers = rejected_claim
    resp = await client.patch(
        f"/api/billing/claims/{claim.id}/resubmission",
        headers=headers,
        json={
            "claim_type": "addition",
            "original_receipt_no": 1234567,
            "original_record_serial": 5,
            "rejection_reason_code": "99",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["rejection_reason_code"] is None


async def test_draft_상태에서는_거부(client, db, approved_doctor):
    doctor, headers = approved_doctor
    patient = Patient(hospital_id=doctor.hospital_id, name="청구환자2", insurance_type="health")
    db.add(patient)
    await db.flush()
    claim = Claim(
        id=uuid.uuid4(),
        patient_id=patient.id,
        doctor_id=doctor.id,
        hospital_id=doctor.hospital_id,
        claim_period_year=2026,
        claim_period_month=6,
        status="draft",
    )
    db.add(claim)
    await db.commit()

    resp = await client.patch(
        f"/api/billing/claims/{claim.id}/resubmission",
        headers=headers,
        json={
            "claim_type": "supplement",
            "original_receipt_no": 1,
            "original_record_serial": 1,
            "rejection_reason_code": "12",
        },
    )
    assert resp.status_code == 409


async def test_이력_테이블에_기록됨(client, db, rejected_claim):
    claim, headers = rejected_claim
    await client.patch(
        f"/api/billing/claims/{claim.id}/resubmission",
        headers=headers,
        json={
            "claim_type": "supplement",
            "original_receipt_no": 111,
            "original_record_serial": 2,
            "rejection_reason_code": "01",
        },
    )
    result = await db.execute(
        select(ClaimResubmissionHistory).where(ClaimResubmissionHistory.claim_id == claim.id)
    )
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].receipt_no == 111
    assert rows[0].record_serial == 2
    assert rows[0].reason_code == "01"
