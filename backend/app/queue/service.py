from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from app.core.models import Claim, DailyQueue
from app.core.timezone import KST, today_kst
from fastapi import HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

VALID_STATUSES = {"waiting", "in_progress", "done", "paid"}
VALID_PAYMENT_METHODS = {"card", "cash"}


async def get_queue_by_date(
    db: AsyncSession, hospital_id: UUID, target_date: date
) -> list[DailyQueue]:
    result = await db.execute(
        select(DailyQueue)
        .options(selectinload(DailyQueue.patient))
        .where(
            DailyQueue.hospital_id == hospital_id,
            DailyQueue.queue_date == target_date
        )
        .order_by(
            case((DailyQueue.status == "done", 1), else_=0).asc(),
            DailyQueue.checked_in_at.asc()
        )
    )
    return result.scalars().all()


async def get_today_queue(db: AsyncSession, hospital_id: UUID) -> list[DailyQueue]:
    return await get_queue_by_date(db, hospital_id, today_kst())


async def get_monthly_queue_counts(
    db: AsyncSession, hospital_id: UUID, year: int, month: int
) -> dict[str, int]:
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    result = await db.execute(
        select(DailyQueue.queue_date, func.count())
        .where(
            DailyQueue.hospital_id == hospital_id,
            DailyQueue.queue_date >= start,
            DailyQueue.queue_date < end,
        )
        .group_by(DailyQueue.queue_date)
    )
    return {queue_date.isoformat(): count for queue_date, count in result.all()}


async def checkin_patient(
    db: AsyncSession,
    hospital_id: UUID,
    patient_id: UUID,
    doctor_id: UUID | None = None,
    source: str = "manual",
    symptom: str | None = None,
) -> DailyQueue:
    today = today_kst()

    max_result = await db.execute(
        select(func.max(DailyQueue.queue_number)).where(
            DailyQueue.hospital_id == hospital_id,
            DailyQueue.queue_date == today,
        )
    )
    queue_number = (max_result.scalar() or 0) + 1

    queue = DailyQueue(
        hospital_id=hospital_id,
        patient_id=patient_id,
        doctor_id=doctor_id,
        queue_date=today,
        source=source,
        status="waiting",
        symptom=symptom,
        queue_number=queue_number,
    )
    db.add(queue)
    await db.commit()
    result = await db.execute(
        select(DailyQueue)
        .options(selectinload(DailyQueue.patient))
        .where(DailyQueue.id == queue.id)
    )
    return result.scalar_one()


async def remove_from_queue(
    db: AsyncSession,
    queue_id: UUID,
    hospital_id: UUID
) -> None:
    result = await db.execute(
        select(DailyQueue).where(
            DailyQueue.id == queue_id,
            DailyQueue.hospital_id == hospital_id
        )
    )
    target_queue = result.scalar_one_or_none()
    if not target_queue:
        raise HTTPException(status_code=404, detail="접수 내역을 찾을 수 없습니다.")
    await db.delete(target_queue)
    await db.commit()


async def update_queue_status(
    db: AsyncSession,
    queue_id: UUID,
    status: str,
    hospital_id: UUID
) -> DailyQueue:
    if status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="유효하지 않은 상태값입니다.")
    result = await db.execute(
        select(DailyQueue)
        .options(selectinload(DailyQueue.patient))
        .where(
            DailyQueue.id == queue_id,
            DailyQueue.hospital_id == hospital_id
        )
    )
    target_queue = result.scalar_one_or_none()
    if not target_queue:
        raise HTTPException(status_code=404, detail="접수 내역을 찾을 수 없습니다.")
    target_queue.status = status
    await db.commit()
    await db.refresh(target_queue)
    return target_queue


async def pay_queue(
    db: AsyncSession,
    queue_id: UUID,
    payment_method: str,
    hospital_id: UUID
) -> DailyQueue:
    if payment_method not in VALID_PAYMENT_METHODS:
        raise HTTPException(status_code=400, detail="유효하지 않은 결제수단입니다.")
    result = await db.execute(
        select(DailyQueue)
        .options(selectinload(DailyQueue.patient))
        .where(
            DailyQueue.id == queue_id,
            DailyQueue.hospital_id == hospital_id
        )
    )
    target_queue = result.scalar_one_or_none()
    if not target_queue:
        raise HTTPException(status_code=404, detail="접수 내역을 찾을 수 없습니다.")
    target_queue.payment_method = payment_method
    target_queue.paid_at = datetime.now(timezone.utc)
    target_queue.status = "paid"
    await db.commit()
    await db.refresh(target_queue)
    return target_queue


async def get_queue_billing(
    db: AsyncSession,
    queue_id: UUID,
    hospital_id: UUID
) -> Claim:
    result = await db.execute(
        select(DailyQueue).where(
            DailyQueue.id == queue_id,
            DailyQueue.hospital_id == hospital_id
        )
    )
    target_queue = result.scalar_one_or_none()
    if not target_queue:
        raise HTTPException(status_code=404, detail="접수 내역을 찾을 수 없습니다.")

    queue_date = target_queue.queue_date
    kst_start = datetime(queue_date.year, queue_date.month, queue_date.day, tzinfo=KST)
    kst_end = kst_start + timedelta(days=1)

    claim_result = await db.execute(
        select(Claim)
        .where(
            Claim.patient_id == target_queue.patient_id,
            Claim.hospital_id == hospital_id,
            Claim.created_at >= kst_start,
            Claim.created_at < kst_end,
        )
        .order_by(Claim.created_at.desc())
    )
    claim = claim_result.scalars().first()
    if not claim:
        raise HTTPException(status_code=404, detail="오늘 날짜의 청구 내역을 찾을 수 없습니다.")
    return claim