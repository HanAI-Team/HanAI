from fastapi import APIRouter, Depends

from app.core.deps import get_current_doctor
from app.diagnosis import service
from app.diagnosis.schema import DiagnosisRequest, DiagnosisResponse

router = APIRouter(tags=["diagnosis"])


@router.post("/", response_model=DiagnosisResponse)
async def diagnose(
    data: DiagnosisRequest,
    current_doctor=Depends(get_current_doctor),
):
    result = service.run_diagnosis(data.transcription)
    return DiagnosisResponse(result=result)
