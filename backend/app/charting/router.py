import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.charting import service
from app.charting.schema import ChartingResponse, MedicalRecordResponse
from app.core.database import get_db
from app.core.deps import get_current_doctor
from app.core.models import Doctor

router = APIRouter(tags=["charting"])


@router.post("/", response_model=ChartingResponse)
async def chart(
    patient_id: uuid.UUID = Form(...),
    audio: UploadFile = File(...),
    current_doctor: Doctor = Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
):
    result = await service.process_chart(
        audio_file=audio,
        patient_id=patient_id,
        doctor_id=UUID(str(current_doctor.id)),
        hospital_id=UUID(str(current_doctor.hospital_id)),
        db=db,
    )
    return ChartingResponse(**result)


@router.get("/{record_id}", response_model=MedicalRecordResponse)
async def get_charts(
    record_id: UUID,
    current_doctor: Doctor = Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
):
    result = await service.get_medical_record(db, current_doctor, record_id)
    return result


@router.get("/patient/{patient_id}", response_model=list[MedicalRecordResponse])
async def get_chart_by_patient(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor),
):
    result = await service.get_records_by_patient(db, patient_id, current_doctor)
    return result

@router.put("/{record_id}/status")
async def 
