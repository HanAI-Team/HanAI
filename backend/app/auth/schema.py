import re
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, field_validator


class RegisterRequest(BaseModel):
    name: str
    license_number: str
    clinic_name: str
    clinic_address: Optional[str] = None
    clinic_phone: Optional[str] = None

    @field_validator("license_number")
    @classmethod
    def license_number_must_be_8_digits(cls, v: str) -> str:
        if not re.fullmatch(r"\d{8}", v):
            raise ValueError("면허번호는 8자리 숫자여야 합니다.")
        return v


class RegisterResponse(BaseModel):
    doctor_id: UUID
    name: str
    clinic_name: str
    message: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AdminApproveResponse(BaseModel):
    doctor_id: UUID
    name: str
    access_token: str
    approved_at: datetime
