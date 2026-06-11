import uuid
from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.charting import service
from app.charting.schema import (
    ChartingResponse,
    FinalizeRecordRequest,
    MedicalRecordResponse,
    UpdateAudioUrlRequest,
    UpdateStatusRequest,
    UpdateMedicalHistoryRequest,
)
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.models import Doctor, StaffAccount

router = APIRouter(tags=["charting"])


@router.post("/", response_model=ChartingResponse)
async def chart(
    patient_id: uuid.UUID = Form(...),
    audio: UploadFile = File(...),
    symptom_text: str | None = Form(None),
    medical_history: str | None = Form(None),
    current_doctor: Doctor | StaffAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await service.process_chart(
        audio_file=audio,
        patient_id=patient_id,
        doctor_id=UUID(str(current_doctor.id)),
        hospital_id=UUID(str(current_doctor.hospital_id)),
        db=db,
        symptom_text=symptom_text,
        medical_history=medical_history,
    )
    return ChartingResponse(**result)


@router.get("/patient/{patient_id}", response_model=list[MedicalRecordResponse])
async def get_patient_records(
    patient_id: uuid.UUID,
    current_doctor: Doctor | StaffAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_records_by_patient(db, patient_id, current_doctor)


@router.get("/{record_id}", response_model=MedicalRecordResponse)
async def get_record(
    record_id: uuid.UUID,
    current_doctor: Doctor | StaffAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_medical_record(db, current_doctor, record_id)


@router.patch("/{record_id}/status", response_model=MedicalRecordResponse)
async def update_status(
    record_id: uuid.UUID,
    data: UpdateStatusRequest,
    current_doctor: Doctor | StaffAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.update_record_status(db, record_id, data.status)


@router.patch("/{record_id}/audio", response_model=MedicalRecordResponse)
async def update_audio(
    record_id: uuid.UUID,
    data: UpdateAudioUrlRequest,
    current_doctor: Doctor | StaffAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.update_audio_url(db, record_id, data.audio_file_url)


@router.patch("/{record_id}/medical-history", response_model=MedicalRecordResponse)
async def update_medical_history(
    record_id: uuid.UUID,
    data: UpdateMedicalHistoryRequest,
    current_doctor: Doctor | StaffAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.update_medical_history(db, record_id, data.medical_history)


@router.patch("/{record_id}/finalize", response_model=MedicalRecordResponse)
async def finalize_record(
    record_id: uuid.UUID,
    data: FinalizeRecordRequest,
    current_doctor: Doctor | StaffAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.finalize_record(
        db, record_id, data.chart_structured, data.selected_result
    )
