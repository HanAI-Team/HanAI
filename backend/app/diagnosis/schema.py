from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class DiagnosisRequest(BaseModel):
    transcription: str
    medical_history: Optional[str] = None


class DiagnosisResponse(BaseModel):
    result: dict


class DiagnosisRecordResponse(BaseModel):
    record_id: UUID
    diagnosis: dict


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str
