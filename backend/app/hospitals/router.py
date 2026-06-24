from uuid import UUID

from app.core.database import get_db
from app.core.deps import get_current_doctor
from app.core.models import Doctor
from app.hospitals import service
from app.hospitals.schema import HospitalResponse, HospitalUpdate
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["hospitals"])


@router.patch("/{hospital_id}", response_model=HospitalResponse)
async def patch_hospital(
    hospital_id: UUID,
    data: HospitalUpdate,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    if doctor.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="병원 정보 수정 권한이 없습니다."
        )

    hospital = await service.update_hospital(db, doctor, hospital_id, data)
    return hospital
