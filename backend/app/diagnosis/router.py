import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_doctor
from app.diagnosis import service
from app.diagnosis.schema import AskRequest, AskResponse, DiagnosisRecordResponse, DiagnosisRequest, DiagnosisResponse

router = APIRouter(tags=["diagnosis"])


@router.post("/", response_model=DiagnosisResponse)
async def diagnose_text(
    data: DiagnosisRequest,
    current_doctor=Depends(get_current_doctor),
):
    result = service.run_diagnosis(data.transcription)
    return DiagnosisResponse(result=result)


@router.post("/ask", response_model=AskResponse)
async def ask(
    data: AskRequest,
    current_doctor=Depends(get_current_doctor),
):
    answer = service.run_ask(data.question)
    return AskResponse(answer=answer)


@router.post("/{record_id}", response_model=DiagnosisRecordResponse)
async def run_diagnosis(
    record_id: uuid.UUID,
    current_doctor=Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
):
    return await service.run_diagnosis_for_record(record_id, db)


@router.get("/{record_id}", response_model=DiagnosisRecordResponse)
async def get_diagnosis(
    record_id: uuid.UUID,
    current_doctor=Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_diagnosis_result(record_id, db)
