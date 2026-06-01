import re
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator


class RegisterVerifyRequest(BaseModel):
    name: str
    license_number: str
    password: str
    jumin: str
    phone: str
    login_option: str = "5"
    clinic_name: str
    clinic_address: Optional[str] = None
    clinic_phone: Optional[str] = None
    telecom_gubun: Optional[str] = None


class RegisterRequest(BaseModel):
    name: str
    license_number: str
    password: str
    clinic_name: str
    clinic_address: Optional[str] = None
    clinic_phone: Optional[str] = None

    @field_validator("license_number")
    @classmethod
    def license_number_must_be_8_digits(cls, v: str) -> str:
        if not re.fullmatch(r"\d{8}", v):
            raise ValueError("면허번호는 8자리 숫자여야 합니다.")
        return v


class LoginRequest(BaseModel):
    license_number: str
    password: str


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


# Staff 관련
class StaffCreateRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "nurse"  # nurse / receptionist


class StaffLoginRequest(BaseModel):
    email: EmailStr
    password: str


class StaffResponse(BaseModel):
    staff_id: UUID
    name: str
    email: str
    role: str
    is_active: bool
