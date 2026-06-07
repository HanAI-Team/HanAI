from uuid import UUID

from pydantic import BaseModel


class DiagnosisRequest(BaseModel):
    transcription: str


class DiagnosisResponse(BaseModel):
    result: dict


class DiagnosisRecordResponse(BaseModel):
    record_id: UUID
    diagnosis: dict


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str
