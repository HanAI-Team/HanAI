from typing import Optional, List
from pydantic import BaseModel


class AcupuncturePointResponse(BaseModel):
    code: str
    korean_name: str
    meridian: Optional[str]
    location: Optional[str]
    is_standalone: bool

    model_config = {"from_attributes": True}


class ConcurrentCheckRequest(BaseModel):
    codes: list[str]


class ConcurrentCheckResponse(BaseModel):
    valid: bool
    conflicting_codes: list[str]
    message: str


class DailyLimitCheckRequest(BaseModel):
    codes: list[str]  # 당일 청구할 침술 행위코드 목록


class DailyLimitCheckResponse(BaseModel):
    valid: bool
    excess_count: int        # 초과 종수
    message: str
