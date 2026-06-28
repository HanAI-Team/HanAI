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
    codes: list[str]


class DailyLimitCheckResponse(BaseModel):
    valid: bool
    excess_count: int
    message: str


class SpecialLimitCheckRequest(BaseModel):
    codes: list[str]


class SpecialLimitCheckResponse(BaseModel):
    valid: bool
    excess_count: int
    message: str
