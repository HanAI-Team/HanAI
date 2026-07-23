import re
from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class HospitalUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    institution_code: Optional[str] = None
    agency_code: Optional[str] = None
    approval_no: Optional[str] = None
    session_timeout_minutes: Optional[int] = None

    @field_validator("institution_code")
    @classmethod
    def validate_institution_code(cls, v: Optional[str]) -> Optional[str]:
        """요양기관기호는 SAM/EDI/처방전 등 모든 청구 관련 출력물에 필수라
        입력 자체를 8자리 숫자로만 허용한다 — 프론트 정규식(/^\\d{8}$/)과 동일한
        검증을 서버에서도 강제해, 직접 API 호출로 형식이 깨진 값이 저장되는
        것을 막는다(2026-07-16, 실제 병원 4곳 전부 미입력 상태로 방치돼 SAM
        생성이 막혀있던 것을 계기로 추가).
        """
        if v is None:
            return v
        if not re.fullmatch(r"\d{8}", v):
            raise ValueError("요양기관기호는 8자리 숫자여야 합니다.")
        return v


class HospitalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    institution_code: Optional[str] = None
    agency_code: Optional[str] = None
    approval_no: Optional[str] = None
    session_timeout_minutes: Optional[int] = None


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
