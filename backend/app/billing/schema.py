from typing import Literal, Optional
from datetime import date
from decimal import Decimal
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


class BillingCalcRequest(BaseModel):
    insurance_type: Literal["4", "5", "7"] = Field(
        description="보험자종별구분. 4=건강보험, 5=의료급여, 7=보훈"
    )
    visit_type: Literal["외래", "입원"]
    benefit_total: int = Field(..., ge=0, description="요양급여비용 총액1 (급여 진료비, 원)")
    non_benefit_total: int = Field(0, ge=0, description="비급여(100분의100) 총액 (원)")
    special_code: Optional[str] = Field(
        None, description="특정기호. 산정특례(V027 등), 차상위(C001/C002)"
    )
    medical_aid_grade: Optional[Literal["1", "2"]] = Field(
        None, description="의료급여 종. 보험자종별=5일 때 필수"
    )
    birth_date: Optional[date] = Field(None, description="환자 생년월일 (15세 이하 입원 판단용)")
    treatment_date: Optional[date] = Field(None, description="진료일 (미입력 시 오늘)")
    work_injury: bool = Field(False, description="공상(산재) 여부")
    disability_medical_cost: int = Field(0, ge=0, description="장애인의료비 (원, 의료급여)")
    support_fund: int = Field(0, ge=0, description="지원금 (원)")
    treatment_days: Decimal = Field(Decimal("0"), description="진료(조제)일수")
    graduated_fee_index: Decimal = Field(Decimal("0"), description="차등지수")


INSURANCE_TYPE_CHOICES = [
    {"value": "4", "label": "건강보험"},
    {"value": "5", "label": "의료급여"},
    {"value": "7", "label": "보훈"},
]

MEDICAL_AID_GRADE_CHOICES = [
    {"value": "1", "label": "의료급여 1종"},
    {"value": "2", "label": "의료급여 2종"},
]


class FeeItem(BaseModel):
    code: str
    name: str
    category: str
    insured_health: bool
    insured_medical_aid: bool
    insured_veterans: bool
    unit_price: int
    is_insured: bool
    effective_date: Optional[date]
    expired_date: Optional[date]


class BillingCalcResponse(BaseModel):
    # 요양급여비용 총액
    benefit_total_1: int
    benefit_total_2: int

    # 청구 핵심 3개
    copayment: int
    claim_amount: int
    upper_limit_excess: int

    # 유형별 본인일부부담금
    health_outpatient_copay: int
    health_inpatient_copay: int
    medical_aid_outpatient_copay: int
    medical_aid_inpatient_copay: int
    near_poverty_1_copay: int
    near_poverty_2_outpatient_copay: int
    near_poverty_2_inpatient_copay: int
    special_exception_copay: int
    work_injury_copay: int
    under_15_inpatient_copay: int
    disability_medical_cost: int
    support_fund: int

    # 100분의100 / 100분의100미만
    full_price_copay_total: int
    under_full_total: int
    under_full_copay: int
    under_full_claim: int

    # 보훈
    veterans_claim: int
    veterans_copay: int
    veterans_total: int
    under_full_veterans_claim: int

    # 차등수가
    treatment_days: Decimal
    graduated_claim: int
    graduated_index: Decimal
