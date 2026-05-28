from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PatientCreate(BaseModel):
    name: str
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    memo: Optional[str] = None


class PatientUpdate(BaseModel):
    phone: Optional[str] = None
    memo: Optional[str] = None


class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    memo: Optional[str] = None
    created_at: datetime


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


class PatientDetailResponse(PatientResponse):
    recent_records: list[RecentRecordSummary]
