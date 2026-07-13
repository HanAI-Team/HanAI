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
    agency_code: Optional[str] = None
    approval_no: Optional[str] = None


class HospitalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    institution_code: Optional[str] = None
    agency_code: Optional[str] = None
    approval_no: Optional[str] = None


class StaffingCreate(BaseModel):
    """MT050(토요일·공휴일 근무현황) 산출용 날짜별 근무 한의사수 등록."""
    work_date: date
    doctor_count: Decimal


class StaffingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    work_date: date
    doctor_count: Decimal


class DoctorWorkDaysCreate(BaseModel):
    """MT008(의사별 진료일수) 산출용 청구월별 의사 근무일수 등록."""
    doctor_id: UUID
    claim_period_year: int
    claim_period_month: int
    work_days: int


class DoctorWorkDaysResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    doctor_id: Optional[UUID] = None
    claim_period_year: int
    claim_period_month: int
    doctor_birth_date: str
    work_days: int
