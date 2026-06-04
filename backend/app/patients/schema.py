from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class PatientCreate(BaseModel):
    name: str
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    memo: Optional[str] = None

    @field_validator("birth_date")
    @classmethod
    def birth_date_must_be_past(cls, v: date) -> date:
        if v and v >= date.today():
            raise ValueError("생년월일은 오늘 이전이어야 합니다.")
        return v


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
