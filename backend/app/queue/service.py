from datetime import date
from uuid import UUID

from app.core.models import DailyQueue
from fastapi import HTTPException
from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

VALID_STATUSES = {"waiting", "in_progress", "done"}


async def get_today_queue(db: AsyncSession, hospital_id: UUID) -> list[DailyQueue]:
    result = await db.execute(
        select(DailyQueue)
        .options(selectinload(DailyQueue.patient))
        .where(
            DailyQueue.hospital_id == hospital_id,
            DailyQueue.queue_date == date.today()
        )
        .order_by(
            case((DailyQueue.status == "done", 1), else_=0).asc(),
            DailyQueue.checked_in_at.asc()
        )
    )
    return result.scalars().all()


async def checkin_patient(
    db: AsyncSession,
    hospital_id: UUID,
    patient_id: UUID,
    doctor_id: UUID | None = None,
    source: str = "manual"
) -> DailyQueue:
    queue = DailyQueue(
        hospital_id=hospital_id,
        patient_id=patient_id,
        doctor_id=doctor_id,
        queue_date=date.today(),
        source=source,
        status="waiting",
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