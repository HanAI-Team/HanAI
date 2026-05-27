import re
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


class LoginRequest(BaseModel):
    license_number: str
    auth_type: str = "naver"


class LoginResponse(BaseModel):
    callback_id: str
    expires_in: int


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
