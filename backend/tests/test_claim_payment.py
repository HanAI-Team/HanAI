"""환자 진료비 수납(ClaimPayment) + 자주 쓰는 항목(FeeMaster) 테스트."""
import uuid

import pytest

from app.core.models import Claim, Patient
from app.billing import payment_service
from app.billing.service import checkout_queue_item, get_quick_fee_items
from app.queue import service as queue_service


@pytest.fixture
async def billed_claim(db, approved_doctor, kcd_codes, fee_master_codes):
    """접수 -> 체크아웃까지 마친 청구 1건."""
    doctor, _ = approved_doctor
    patient = Patient(hospital_id=doctor.hospital_id, name="김수납", insurance_type="health")
    db.add(patient)
    await db.commit()
    await db.refresh(patient)

    queue = await queue_service.checkin_patient(db, doctor.hospital_id, patient.id)
    claim = await checkout_queue_item(
        db, doctor.hospital_id, doctor, queue,
        kcd_code="B001",
        line_items=[{"code": "AA159", "qty": 1, "days": 1}],
    )
    return claim, queue, doctor


async def test_수납_처리하면_접수상태_paid로_전환(db, billed_claim):
    claim, queue, doctor = billed_claim
    payment = await payment_service.create_payment(
        db, doctor.hospital_id, claim.id, method="cash", amount=claim.claim_amount,
        processed_by_name=doctor.name,
    )
    assert payment.method == "cash"
    await db.refresh(queue)
    assert queue.status == "paid"


async def test_존재하지않는_청구_수납시_에러(db, approved_doctor):
    doctor, _ = approved_doctor
    import uuid
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        await payment_service.create_payment(
            db, doctor.hospital_id, uuid.uuid4(), method="cash", amount=1000,
            processed_by_name=doctor.name,
        )


async def test_수납내역_조회_필터(db, billed_claim):
    claim, queue, doctor = billed_claim
    await payment_service.create_payment(
        db, doctor.hospital_id, claim.id, method="card", amount=1000,
        processed_by_name=doctor.name,
    )
    total, rows = await payment_service.list_payments(
        db, doctor.hospital_id, start_date=None, end_date=None, method=None, page=1, size=20
    )
    assert total == 1
    payment, c, patient = rows[0]
    assert payment.method == "card"
    assert patient.name == "김수납"

    # method 필터로 걸러지는지
    total_cash, rows_cash = await payment_service.list_payments(
        db, doctor.hospital_id, start_date=None, end_date=None, method="cash", page=1, size=20
    )
    assert total_cash == 0


async def test_수납_요약_오늘_이번달_비율(db, billed_claim):
    claim, queue, doctor = billed_claim
    await payment_service.create_payment(
        db, doctor.hospital_id, claim.id, method="cash", amount=3000,
        processed_by_name=doctor.name,
    )
    summary = await payment_service.get_payment_summary(
        db, doctor.hospital_id, start_date=None, end_date=None, method=None
    )
    assert summary["today_total"] == 3000
    assert summary["month_total"] == 3000
    assert summary["cash_ratio"] == 100.0
    assert summary["card_ratio"] == 0.0


async def test_자주쓰는항목_카테고리별_목록(db, approved_doctor, fee_master_codes):
    doctor, _ = approved_doctor
    result = await get_quick_fee_items(db, doctor.hospital_id)
    assert "침술" in result["categories"]
    assert any(item["code"] == "AA159" for item in result["by_category"]["침술"])


async def test_자주쓰는항목_빈도상위_favorites(db, billed_claim):
    claim, queue, doctor = billed_claim
    # billed_claim fixture가 AA159를 이미 1회 사용
    result = await get_quick_fee_items(db, doctor.hospital_id)
    favorite_codes = [f["code"] for f in result["favorites"]]
    assert "AA159" in favorite_codes


async def test_청구목록_접수건은_수납전엔_잠기고_수납후_풀린다(client, db, billed_claim, approved_doctor):
    """접수 대시보드에서 만들어진 청구(from_reception=True)는 수납 전엔 is_paid=False로
    내려와 프론트가 EDI/영수증/명세서 버튼을 잠글 수 있고, 수납 처리 후엔 True로 바뀐다."""
    claim, queue, doctor = billed_claim
    _, headers = approved_doctor

    resp = await client.get("/api/billing/claims", headers=headers)
    assert resp.status_code == 200, resp.text
    item = next(i for i in resp.json() if i["id"] == str(claim.id))
    assert item["from_reception"] is True
    assert item["is_paid"] is False

    await payment_service.create_payment(
        db, doctor.hospital_id, claim.id, method="cash", amount=claim.claim_amount,
        processed_by_name=doctor.name,
    )

    resp2 = await client.get("/api/billing/claims", headers=headers)
    item2 = next(i for i in resp2.json() if i["id"] == str(claim.id))
    assert item2["is_paid"] is True


async def test_청구목록_레거시청구는_from_reception_false(client, db, approved_doctor):
    """접수 대시보드를 거치지 않고(레거시 진료 플로우로) 만들어진 청구는
    수납 기록이 없어도 from_reception=False로 내려와 문서 버튼이 잠기지 않아야 한다."""
    doctor, headers = approved_doctor
    patient = Patient(hospital_id=doctor.hospital_id, name="레거시환자", insurance_type="health")
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
        status="draft",
    )
    db.add(claim)
    await db.commit()

    resp = await client.get("/api/billing/claims", headers=headers)
    assert resp.status_code == 200, resp.text
    item = next(i for i in resp.json() if i["id"] == str(claim.id))
    assert item["from_reception"] is False
    assert item["is_paid"] is False
