from uuid import UUID

from app.core.deps import get_current_user, get_db
from app.queue import service
from app.queue.schema import QueueCreateRequest, QueueResponse, QueueStatusUpdateRequest
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/queue", tags=["queue"])

@router.get("/today", response_model=list[QueueResponse])
async def get_queue_today(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    queues = await service.get_today_queue(db, current_user.hospital_id)
    return [QueueResponse.from_orm_with_patient(q) for q in queues]

@router.post("/", response_model=QueueResponse)
async def checkin(
    body: QueueCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    queue = await service.checkin_patient(
        db,
        hospital_id=current_user.hospital_id,
        patient_id=body.patient_id,
        doctor_id=body.doctor_id,
        source="manual",
    )
    return QueueResponse.from_orm_with_patient(queue)

@router.delete("/{queue_id}", status_code=204)
async def cancel_checkin(
    queue_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await service.remove_from_queue(db, queue_id, current_user.hospital_id)



@router.patch("/{queue_id}/status", response_model=QueueResponse)
async def change_status(
    queue_id: UUID,
    body: QueueStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    queue = await service.update_queue_status(
        db, queue_id, body.status, current_user.hospital_id
    )
    return QueueResponse.from_orm_with_patient(queue)