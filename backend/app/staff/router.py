from uuid import UUID

from app.auth.service import record_account_history
from app.core.database import get_db
from app.core.deps import get_current_doctor
from app.core.models import Doctor
from app.staff import service
from app.staff.schema import StaffCreateRequest, StaffResponse
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["staff"])


@router.post("/", response_model=StaffResponse, status_code=201)
async def create_staff(
    data: StaffCreateRequest,
    doctor: Doctor = Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
):
    # owner만 가능하도록 권한 체크
    # service.create_staff 호출
    if str(doctor.role) != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="owner 계정만 접근 가능합니다.",
        )
    staff =  await service.create_staff(
        db=db, hospital_id=UUID(str(doctor.hospital_id)), data=data
    )
    await record_account_history(
        db, "staff", staff.id, "created", 
        actor_id=doctor.id
    )
    await db.commit()
    return staff 


@router.get("/", response_model=list[StaffResponse])
async def get_staff_list(
    doctor: Doctor = Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_staff_list(
        db=db, hospital_id=UUID(str(doctor.hospital_id))
    )


@router.patch("/{staff_id}/deactivate", response_model=StaffResponse)
async def deactivate_staff(
    staff_id: UUID,
    doctor: Doctor = Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
):
    if str(doctor.role) != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="owner 계정만 접근 가능합니다.",
        )
    staff =  await service.deactivate_staff(
        db=db, hospital_id=UUID(str(doctor.hospital_id)), staff_id=staff_id
    )
    await record_account_history(
        db, "staff", staff.id, "deactivated", 
        actor_id=doctor.id
    )
    await db.commit()
    return staff 




@router.patch("/{staff_id}/activate", response_model=StaffResponse)
async def activate_staff(
    staff_id: UUID,
    doctor: Doctor = Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
):
    if str(doctor.role) != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="owner 계정만 접근 가능합니다.",
        )
    staff =  await service.activate_staff(
        db=db, hospital_id=UUID(str(doctor.hospital_id)), staff_id=staff_id
    )

    await record_account_history(
    db, "staff", staff.id, "role_changed",
    actor_id=doctor.id,
    detail="reactivated"
    )
    await db.commit()
    return staff 
