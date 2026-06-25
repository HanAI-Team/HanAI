from typing import Optional, List
from datetime import date
from pydantic import BaseModel


class KcdUCodeResponse(BaseModel):
    code: str
    korean_name: str
    hanja: Optional[str]
    category: Optional[str]
    effective_date: Optional[date]
    expired_date: Optional[date]

    model_config = {"from_attributes": True}


class KcdValidateRequest(BaseModel):
    codes: List[str]
    as_of: Optional[date] = None
    patient_gender: Optional[str] = None  # "M" 또는 "F"


class KcdValidateResult(BaseModel):
    code: str
    is_valid: bool
    korean_name: Optional[str] = None
    is_notifiable: Optional[bool] = None  # 법정감염병 여부
    error: Optional[str] = None


class KcdValidateResponse(BaseModel):
    results: List[KcdValidateResult]
    has_error: bool
