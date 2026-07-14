"""환자 진료비 수납(ClaimPayment) + 자주 쓰는 항목(FeeMaster) 테스트."""
import pytest

from app.core.models import Patient
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
