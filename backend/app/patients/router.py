from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.core.database import get_db
from app.core.deps import get_current_doctor
from app.core.models import Doctor
from app.patients import service
from app.patients.schema import (
    PatientCreate,
    PatientUpdate,
    PatientListResponse,
    PatientResponse,
    RecentRecordSummary,
)

router = APIRouter(tags=["patients"])


@router.get("/", response_model=PatientListResponse)
async def get_patients(
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
    page: int = 1,
    size: int = 1,
    search: str | None = None,
):
    patients, total = await service.get_patients(db, doctor, page, size, search)
    if not patients:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="등록된 회원이 없습니다."
        )
    return PatientListResponse(
        total=total,
        page=page,
        size=size,
        items=[PatientResponse.model_validate(p) for p in patients],
    )


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    patient = await service.get_patient(db, doctor, patient_id)

    return patient


@router.post(
    "/register", response_model=PatientResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    data: PatientCreate,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):

    patient = await service.create_patient(db, doctor, data)
    return patient


@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: UUID,
    data: PatientUpdate,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    patient = await service.update_patient(db, doctor, patient_id, data)

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="등록되지 않은 회원입니다."
        )
    return patient


@router.get("/{patient_id}/records")
async def get_patient_records(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    patient, records = await service.get_patient_with_records(db, doctor, patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="등록되지 않은 회원입니다."
        )
    return {
        "patient": PatientResponse.model_validate(patient),
        "records": [RecentRecordSummary.model_validate(r) for r in records],
    }
