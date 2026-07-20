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
    sex_restriction: Optional[str] = None  # "M"=남성만, "F"=여성만, None=제한없음
    is_notifiable: bool = False            # 법정감염병 여부

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
    sex_restriction: Optional[str] = None  # 코드에 설정된 성별 제한 ("M"/"F"/None)
    reason: Optional[str] = None          # "not_found" | "expired" | "gender_mismatch"
    error: Optional[str] = None


class KcdValidateResponse(BaseModel):
    results: List[KcdValidateResult]
    has_error: bool


class KcdCodeCreate(BaseModel):
    code: str
    korean_name: str
    hanja: Optional[str] = None
    category: Optional[str] = None
    effective_date: Optional[date] = None
    expired_date: Optional[date] = None
    sex_restriction: Optional[str] = None
    is_notifiable: bool = False


class KcdCodeUpdate(BaseModel):
    korean_name: Optional[str] = None
    hanja: Optional[str] = None
    category: Optional[str] = None
    effective_date: Optional[date] = None
    expired_date: Optional[date] = None
    sex_restriction: Optional[str] = None
    is_notifiable: Optional[bool] = None
