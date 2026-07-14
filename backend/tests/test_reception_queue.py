"""접수 대시보드(DailyQueue) — 베드 배정/달력 집계/청구 모달 체크아웃 테스트."""
from datetime import date

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.core.models import Claim, ClaimLineItem, MedicalRecord, Patient
from app.billing.service import checkout_queue_item, preview_checkout_billing
from app.queue import service as queue_service


@pytest.fixture
async def patient(db, approved_doctor):
    doctor, _ = approved_doctor
    p = Patient(hospital_id=doctor.hospital_id, name="김환자", insurance_type="health")
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


async def test_접수_등록_기본상태는_waiting(db, approved_doctor, patient):
    doctor, _ = approved_doctor
    queue = await queue_service.checkin_patient(db, doctor.hospital_id, patient.id)
    assert queue.status == "waiting"
    assert queue.assigned_bed is None


async def test_베드_배정(db, approved_doctor, patient):
    doctor, _ = approved_doctor
    queue = await queue_service.checkin_patient(db, doctor.hospital_id, patient.id)
    updated = await queue_service.update_queue_bed(db, queue.id, "1번", doctor.hospital_id)
    assert updated.assigned_bed == "1번"


async def test_날짜별_접수목록_조회(db, approved_doctor, patient):
    doctor, _ = approved_doctor
    await queue_service.checkin_patient(db, doctor.hospital_id, patient.id)
    today_list = await queue_service.get_queue_by_date(db, doctor.hospital_id, date.today())
    assert len(today_list) == 1
    other_day_list = await queue_service.get_queue_by_date(db, doctor.hospital_id, date(2020, 1, 1))
    assert len(other_day_list) == 0


async def test_달력_집계(db, approved_doctor, patient):
    doctor, _ = approved_doctor
    await queue_service.checkin_patient(db, doctor.hospital_id, patient.id)
    counts = await queue_service.get_queue_calendar(
        db, doctor.hospital_id, date.today().year, date.today().month
    )
    assert counts.get(date.today().isoformat()) == 1


async def test_체크아웃_상병코드_없으면_에러(db, approved_doctor, patient, kcd_codes):
    doctor, _ = approved_doctor
    queue = await queue_service.checkin_patient(db, doctor.hospital_id, patient.id)
    with pytest.raises(HTTPException):
        await checkout_queue_item(
            db, doctor.hospital_id, doctor, queue,
            kcd_code="ZZZZZ",  # 완전코드 목록에 없음
            line_items=[{"code": "AA159", "qty": 1, "days": 1}],
        )


async def test_체크아웃_처방없으면_에러(db, approved_doctor, patient, kcd_codes):
    doctor, _ = approved_doctor
    queue = await queue_service.checkin_patient(db, doctor.hospital_id, patient.id)
    with pytest.raises(HTTPException):
        await checkout_queue_item(
            db, doctor.hospital_id, doctor, queue,
            kcd_code="B001", line_items=[],
        )


async def test_체크아웃_정상_처리(db, approved_doctor, patient, kcd_codes, fee_master_codes):
    doctor, _ = approved_doctor
    queue = await queue_service.checkin_patient(db, doctor.hospital_id, patient.id)

    claim = await checkout_queue_item(
        db, doctor.hospital_id, doctor, queue,
        kcd_code="B001",
        line_items=[
            {"code": "AA159", "qty": 1, "days": 1},
            {"code": "AA161", "qty": 1, "days": 2},
        ],
    )

    # MedicalRecord가 새로 생성되고 상병코드가 저장됨
    r = await db.execute(select(MedicalRecord).where(MedicalRecord.claim_id == claim.id))
    record = r.scalar_one()
    assert record.kcd_code == "B001"

    # ClaimLineItem 2건, 금액 = 1000*1*1 + 1000*1*2 = 3000
    r_items = await db.execute(select(ClaimLineItem).where(ClaimLineItem.claim_id == claim.id))
    items = r_items.scalars().all()
    assert len(items) == 2
    assert claim.total_amount == 3000

    # 접수 상태가 billed로 전환되고 claim_id가 연결됨
    await db.refresh(queue)
    assert queue.status == "billed"
    assert queue.claim_id == claim.id


async def test_체크아웃_존재하지않는_수가코드_에러(db, approved_doctor, patient, kcd_codes, fee_master_codes):
    doctor, _ = approved_doctor
    queue = await queue_service.checkin_patient(db, doctor.hospital_id, patient.id)
    with pytest.raises(HTTPException):
        await checkout_queue_item(
            db, doctor.hospital_id, doctor, queue,
            kcd_code="B001",
            line_items=[{"code": "NOT_EXIST", "qty": 1, "days": 1}],
        )


async def test_청구_미리보기_금액이_실제_체크아웃과_일치(db, approved_doctor, patient, kcd_codes, fee_master_codes):
    """청구 모달의 실시간 미리보기(preview_checkout_billing)는 DB를 변경하지 않고
    실제 저장(checkout_queue_item)과 동일한 계산 결과를 내야 한다."""
    doctor, _ = approved_doctor
    queue = await queue_service.checkin_patient(db, doctor.hospital_id, patient.id)
    line_items = [
        {"code": "AA159", "qty": 1, "days": 1},
        {"code": "AA161", "qty": 1, "days": 2},
    ]

    preview = await preview_checkout_billing(db, patient.id, line_items)

    r_claims = await db.execute(select(Claim))
    assert r_claims.scalars().all() == []
    r_records = await db.execute(select(MedicalRecord))
    assert r_records.scalars().all() == []

    claim = await checkout_queue_item(
        db, doctor.hospital_id, doctor, queue,
        kcd_code="B001", line_items=line_items,
    )

    assert preview["total_amount"] == claim.total_amount == 3000
    assert preview["patient_copay"] == claim.patient_copay
    assert preview["claim_amount"] == claim.claim_amount


async def test_청구_미리보기_처방없으면_에러(db, approved_doctor, patient):
    with pytest.raises(HTTPException):
        await preview_checkout_billing(db, patient.id, [])


async def test_청구_미리보기_존재하지않는_수가코드_에러(db, approved_doctor, patient, fee_master_codes):
    with pytest.raises(HTTPException):
        await preview_checkout_billing(db, patient.id, [{"code": "NOT_EXIST", "qty": 1, "days": 1}])
