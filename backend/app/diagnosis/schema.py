from pydantic import BaseModel


class DiagnosisRequest(BaseModel):
    transcription: str


class DiagnosisResponse(BaseModel):
    result: dict
