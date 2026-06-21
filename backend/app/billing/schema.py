from typing import Literal, Optional
from datetime import date
from pydantic import BaseModel, Field


class HerbItem(BaseModel):
    name: str
    dosage_g: float = Field(..., gt=0, description="1일 용량 (g)")
    price_won: Optional[float] = Field(None, description="약재 단가 (원, 임의처방 시 필요)")
    role: Literal["base", "added", "removed"] = Field(
        "base",
        description=(
            "약재 역할 구분. "
            "base=기준처방 구성약재(가감 없음), "
            "added=가미(加味, 기준처방에 추가한 약재), "
            "removed=감미(減味, 기준처방에서 제외한 약재)"
        ),
    )


class PrescriptionCheckRequest(BaseModel):
    type: Literal["기준처방", "가감처방", "가미제", "임의처방"]
    herbs: list[HerbItem]
    patient_birth_date: Optional[date] = Field(
        None,
        description="소아 용량 비율 계산용 생년월일. 없으면 성인 기준(비율 1.0)으로 검증",
    )


class ViolationItem(BaseModel):
    rule: str
    detail: str


class PrescriptionCheckResponse(BaseModel):
    valid: bool
    violations: list[ViolationItem]
