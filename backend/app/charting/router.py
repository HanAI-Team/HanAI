import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.charting import service
from app.charting.schema import ChartingResponse
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
        doctor_id=current_doctor.id,
        hospital_id=current_doctor.hospital_id,
        db=db,
    )
    return ChartingResponse(**result)
