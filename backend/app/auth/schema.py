import re
from datetime import date, datetime
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
    def license_number_must_be_digits(cls, v: str) -> str:
        if not re.fullmatch(r"\d{4,}", v):
            raise ValueError("면허번호는 4자리 이상 숫자여야 합니다.")
        return v
    @field_validator("password")
    @classmethod
    def password_complexity(cls, v:str)->str:
        from app.auth.service import validate_password_complexity
        errors = validate_password_complexity(v)
        if errors:
            raise ValueError("/".join(errors))
        return v


class ResetPasswordResponse(BaseModel):
    temp_password: str


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


class PendingDoctorResponse(BaseModel):
    doctor_id: UUID
    name: str
    license_number: str
    clinic_name: str
    created_at: datetime


# Staff 관련
class StaffCreateRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "nurse"  # nurse / receptionist

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        from app.auth.service import validate_password_complexity
        errors = validate_password_complexity(v)
        if errors:
            raise ValueError("/".join(errors))
        return v


class StaffLoginRequest(BaseModel):
    username: str
    password: str


class StaffResponse(BaseModel):
    staff_id: UUID
    name: str
    email: str
    role: str
    is_active: bool


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    @field_validator("new_password")
    @classmethod
    def password_complexity(cls, v:str)->str:
        from app.auth.service import validate_password_complexity
        errors = validate_password_complexity(v)
        if errors:
            raise ValueError("/".join(errors))
        return v



class DoctorProfileUpdate(BaseModel):
    birth_date: Optional[date] = None


class VerifyInitResponse(BaseModel):
    callback_id: str
    callback_type: str
    message: str = "앱에서 인증을 완료한 후 confirm을 호출해주세요."


class VerifyConfirmRequest(BaseModel):
    callback_id: str
    callback_type: str = "SIMPLE"
    callback_data: str = ""
    # 회원가입 데이터
    name: str
    license_number: str
    password: str
    clinic_name: str
    clinic_address: Optional[str] = None
    clinic_phone: Optional[str] = None
