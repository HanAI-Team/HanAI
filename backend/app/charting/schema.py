from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ChartingResponse(BaseModel):
    record_id: UUID
    transcription: str
    diagnosis: dict


class UpdateMedicalHistoryRequest(BaseModel):
    medical_history: Optional[str] = None


class FinalizeRecordRequest(BaseModel):
    chart_structured: str


class MedicalRecordResponse(BaseModel):
    id: UUID
    patient_id: UUID
    doctor_id: UUID
    hospital_id: UUID
    raw_transcription: Optional[str] = None
    chart_structured: Optional[str] = None
    audio_file_url: Optional[str] = None
    status: str
    recorded_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UpdateStatusRequest(BaseModel):
    status: str  # recording / transcribing / completed / failed


class UpdateAudioUrlRequest(BaseModel):
    audio_file_url: str
