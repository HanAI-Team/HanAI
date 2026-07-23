from datetime import date, datetime
from typing import Optional
from uuid import UUID

from app.core.timezone import today_kst
from pydantic import BaseModel, ConfigDict, field_validator


class PatientCreate(BaseModel):
    name: str
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    memo: Optional[str] = None

    @field_validator("birth_date")
    @classmethod
    def birth_date_must_be_past(cls, v: date) -> date:
        if v and v >= today_kst():
            raise ValueError("생년월일은 오늘 이전이어야 합니다.")
        return v


class PatientUpdate(BaseModel):
    name: Optional[str] = None
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    memo: Optional[str] = None
    insurance_type: Optional[str] = None
    rrn: Optional[str] = None
    disability_grade: Optional[str] = None
    medical_aid_grade: Optional[str] = None


class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    memo: Optional[str] = None
    created_at: datetime
    insurance_type: Optional[str] = None
    disability_grade: Optional[str] = None
    medical_aid_grade: Optional[str] = None
    rrn_masked: Optional[str] = None


class PatientListResponse(BaseModel):
    total: int
    page: int
    size: int
    items: list[PatientResponse]


class RecentRecordSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    recorded_at: Optional[datetime] = None
    chart_structured: Optional[str] = None
    medical_history: Optional[str] = None
    raw_transcription: Optional[str] = None
    kcd_code: Optional[str] = None
    secondary_kcd_codes: Optional[list[str]] = None


class PatientDetailResponse(PatientResponse):
    recent_records: list[RecentRecordSummary]


class PatientRecordListResponse(BaseModel):
    total: int
    page: int
    size: int
    items: list[RecentRecordSummary]


class DataPurgeLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    doctor_id: UUID
    patient_name_before: Optional[str] = None
    reason: str
    purge_type: str
    purged_at: str


class DataPurgeLogListResponse(BaseModel):
    total: int
    page: int
    size: int
    items: list[DataPurgeLogResponse]


class RecordCreate(BaseModel):
    chart_structured: str
    raw_transcription: Optional[str] = None
    medical_history: Optional[str] = None
    selected_result: Optional[str] = None
