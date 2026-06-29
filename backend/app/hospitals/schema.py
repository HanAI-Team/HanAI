from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class HospitalUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    institution_code: Optional[str] = None


class HospitalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    institution_code: Optional[str] = None


class StaffingCreate(BaseModel):
    """MT050(토요일·공휴일 근무현황) 산출용 날짜별 근무 한의사수 등록."""
    work_date: date
    doctor_count: Decimal


class StaffingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    work_date: date
    doctor_count: Decimal
