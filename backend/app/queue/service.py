from datetime import date
from uuid import UUID

from app.core.models import DailyQueue
from fastapi import HTTPException
from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


# 1. 오늘 접수 목록 조회
async def get_today_queue(db: AsyncSession, hospital_id: UUID) -> list[DailyQueue]:
    result = await db.execute(
        select(DailyQueue)
        .options(selectinload(DailyQueue.patient))
        .where(
            DailyQueue.hospital_id == hospital_id,
            DailyQueue.queue_date == date.today()
        )
        .order_by(
            case(
                (DailyQueue.status == "done", 1),
                else_=0
            ).asc(),
            DailyQueue.checked_in_at.asc()
        )
    )
    return result.scalars().all()

# 2. 환자 접수 (manual)

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

# 3. 접수 취소
async def remove_from_queue(db, queue_id, hospital_id):
    # 본인 병원 queue만 삭제 가능 확인
    result  = await db.execute(select(DailyQueue).where(DailyQueue.id == queue_id, DailyQueue.hospital_id == hospital_id))
    target_queue = result.scalar_one_or_none()
    if not target_queue:
        raise HTTPException(status_code=404, detail="접수 내역을 찾을 수 없습니다.")
    await db.delete(target_queue)
    await db.commit()

VALID_STATUSES = {"waiting", "in_progress", "done"}


async def update_queue_status(db, queue_id, status, hospital_id):
    # waiting / in_progress / done
    result = await db.execute(select(DailyQueue).where(DailyQueue.hospital_id == hospital_id, DailyQueue.id == queue_id))
    target_queue = result.scalar_one_or_not()
    if not target_queue:
        raise HTTPException(status_code=404, detail="접수 내역을 찾을 수 없습니다.")
    
    if status  not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="")

    target_queue.status = status

    await db.commit()
    await db.refresh(target_queue)
    return target_queue
    
