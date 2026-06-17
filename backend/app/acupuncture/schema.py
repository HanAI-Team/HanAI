from typing import Optional
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
