from uuid import UUID

from app.core.database import get_db
from app.core.deps import get_current_doctor
from app.core.models import Doctor
from app.hospitals import service
from app.hospitals.schema import (
    DoctorWorkDaysCreate,
    DoctorWorkDaysResponse,
    HospitalResponse,
    HospitalUpdate,
    StaffingCreate,
    StaffingResponse,
)
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


@router.post("/{hospital_id}/saturday-holiday-staffing", response_model=StaffingResponse)
async def create_staffing(
    hospital_id: UUID,
    data: StaffingCreate,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    if doctor.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="근무현황 등록 권한이 없습니다."
        )

    return await service.create_staffing(db, doctor, hospital_id, data)


@router.get("/{hospital_id}/saturday-holiday-staffing", response_model=list[StaffingResponse])
async def list_staffing(
    hospital_id: UUID,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    return await service.list_staffing(db, doctor, hospital_id)


@router.post("/{hospital_id}/doctor-work-days", response_model=DoctorWorkDaysResponse)
async def create_doctor_work_days(
    hospital_id: UUID,
    data: DoctorWorkDaysCreate,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    if doctor.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="근무일수 등록 권한이 없습니다."
        )

    return await service.create_doctor_work_days(db, doctor, hospital_id, data)


@router.get("/{hospital_id}/doctor-work-days", response_model=list[DoctorWorkDaysResponse])
async def list_doctor_work_days(
    hospital_id: UUID,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    return await service.list_doctor_work_days(db, doctor, hospital_id)
