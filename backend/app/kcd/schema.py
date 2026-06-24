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
    codes: List[str]            # 검증할 상병코드 목록 (예: ["U234", "A001"])
    as_of: Optional[date] = None  # 기준일 (기본: 오늘)


class KcdValidateResult(BaseModel):
    code: str                       # 입력된 코드
    is_valid: bool                  # 완전코드 여부 (마스터 존재 + 유효기간 내)
    korean_name: Optional[str] = None  # 유효한 경우 한글명
    error: Optional[str] = None    # 유효하지 않은 경우 사유


class KcdValidateResponse(BaseModel):
    results: List[KcdValidateResult]
    has_error: bool                 # 하나라도 invalid면 True
