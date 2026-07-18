from datetime import date
from uuid import UUID

from app.core.deps import get_current_user, get_db
from app.core.models import Doctor
from app.core.timezone import today_kst
from app.queue import service
from app.queue.schema import (
    QueueBillingResponse,
    QueueCreateRequest,
    QueueMonthlyCountsResponse,
    QueuePayRequest,
    QueueResponse,
    QueueStatusUpdateRequest,
)
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/queue", tags=["queue"])

@router.get("/today", response_model=list[QueueResponse])
async def get_queue_today(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    queues = await service.get_today_queue(db, current_user.hospital_id)
    return [QueueResponse.from_orm_with_patient(q) for q in queues]

@router.get("/monthly-counts", response_model=QueueMonthlyCountsResponse)
async def get_monthly_queue_counts(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    counts = await service.get_monthly_queue_counts(
        db, current_user.hospital_id, year, month
    )
    return QueueMonthlyCountsResponse(counts=counts)

@router.get("/", response_model=list[QueueResponse])
async def get_queue_by_date(
    queue_date: date | None = Query(None, alias="date"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    queues = await service.get_queue_by_date(
        db, current_user.hospital_id, queue_date or today_kst()
    )
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
        symptom=body.symptom,
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

@router.patch("/{queue_id}/pay", response_model=QueueResponse)
async def pay_queue(
    queue_id: UUID,
    body: QueuePayRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if isinstance(current_user, Doctor) and str(current_user.role) != "owner":
        raise HTTPException(status_code=403, detail="owner 또는 staff 계정만 접근 가능합니다.")
    queue = await service.pay_queue(
        db, queue_id, body.payment_method, current_user.hospital_id
    )
    return QueueResponse.from_orm_with_patient(queue)

@router.get("/{queue_id}/billing", response_model=QueueBillingResponse)
async def get_queue_billing(
    queue_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    claim = await service.get_queue_billing(db, queue_id, current_user.hospital_id)
    return QueueBillingResponse(
        claim_id=claim.id,
        claim_amount=claim.claim_amount,
        total_amount=claim.total_amount,
        patient_copay=claim.patient_copay,
    )