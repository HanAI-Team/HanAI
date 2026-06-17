from typing import Literal, Optional
from pydantic import BaseModel, Field


class HerbItem(BaseModel):
    name: str
    dosage_g: float = Field(..., gt=0, description="1일 용량 (g)")
    price_won: Optional[float] = Field(None, description="약재 단가 (원, 임의처방 시 필요)")


class PrescriptionCheckRequest(BaseModel):
    type: Literal["가미제", "임의처방"]
    herbs: list[HerbItem]


class ViolationItem(BaseModel):
    rule: str
    detail: str


class PrescriptionCheckResponse(BaseModel):
    valid: bool
    violations: list[ViolationItem]
