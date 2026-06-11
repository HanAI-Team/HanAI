import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_doctor
from app.core.redis import check_rate_limit
from app.diagnosis import service
from app.diagnosis.schema import AskRequest, AskResponse, DiagnosisRecordResponse, DiagnosisRequest, DiagnosisResponse

router = APIRouter(tags=["diagnosis"])


@router.post("/", response_model=DiagnosisResponse)
async def diagnose_text(
    data: DiagnosisRequest,
    current_doctor=Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
):
    allowed = await check_rate_limit(f"diagnosis:{current_doctor.id}", limit=3, window_seconds=60)
    if not allowed:
        raise HTTPException(status_code=429, detail="요청이 너무 많습니다. 1분 후 다시 시도해주세요.")
    transcription = data.transcription
    if data.medical_history and data.medical_history.strip():
        transcription += f"\n\n[기존 병력]\n{data.medical_history.strip()}"
    result = await service.run_diagnosis(transcription)
    return DiagnosisResponse(result=result)


@router.post("/ask", response_model=AskResponse)
async def ask(
    data: AskRequest,
    current_doctor=Depends(get_current_doctor),
):
    allowed = await check_rate_limit(f"diagnosis_ask:{current_doctor.id}", limit=10, window_seconds=60)
    if not allowed:
        raise HTTPException(status_code=429, detail="요청이 너무 많습니다. 1분 후 다시 시도해주세요.")
    answer = service.run_ask(data.question)
    return AskResponse(answer=answer)


@router.post("/public-ask", response_model=AskResponse)
async def public_ask(data: AskRequest):
    answer = service.run_ask(data.question)
    return AskResponse(answer=answer)


@router.post("/{record_id}", response_model=DiagnosisRecordResponse)
async def run_diagnosis(
    record_id: uuid.UUID,
    current_doctor=Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
):
    allowed = await check_rate_limit(f"diagnosis:{current_doctor.id}", limit=3, window_seconds=60)
    if not allowed:
        raise HTTPException(status_code=429, detail="요청이 너무 많습니다. 1분 후 다시 시도해주세요.")
    return await service.run_diagnosis_for_record(record_id, db)


@router.get("/{record_id}", response_model=DiagnosisRecordResponse)
async def get_diagnosis(
    record_id: uuid.UUID,
    current_doctor=Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_diagnosis_result(record_id, db)
