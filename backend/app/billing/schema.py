from datetime import date
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


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


class ProcedureItem(BaseModel):
    """진료내역 한 줄 — EDI 명세서진료내역 레코드와 1:1 대응."""
    hang: Literal["01", "02", "03", "04", "05", "L"] = Field(
        "04", description="항번호. 04=시술및처치료"
    )
    mok: Literal["01", "02", "03", "04", "99"] = Field(
        description="목번호. 01=침술 02=구술 03=부항술 04=처치료 99=기타"
    )
    code_gubun: Literal["A", "B", "C", "H"] = Field(
        "A", description="코드구분. A=수가 B=전용수가 C=약가 H=치료재료"
    )
    code: str = Field(..., max_length=9, description="행위코드 (예: AA159)")
    unit_price: Decimal = Field(..., ge=0, description="단가 (원)")
    qty: Decimal = Field(..., gt=0, description="1일투여량/실시횟수")
    days: int = Field(..., ge=1, description="총투여일수/실시횟수")
    amount: int = Field(..., ge=0, description="금액 = 단가 × qty × days (원)")
    license_type: Literal["3", "6", "7"] = Field(
        "3", description="면허종류. 3=한의사 6=간호사 7=사회복지사"
    )
    license_no: str = Field("", max_length=10, description="면허번호")
    hyeolmyeong_names: list[str] = Field(
        default_factory=list,
        description="혈명 목록. 침술(hang=04, mok=01)일 때 JS011 특정내역으로 변환됨",
    )


class BillingCalcRequest(BaseModel):
    insurance_type: Literal["4", "5", "7"] = Field(
        description="보험자종별구분. 4=건강보험, 5=의료급여, 7=보훈"
    )
    visit_type: Literal["외래", "입원"]
    benefit_total: int = Field(..., ge=0, description="요양급여비용 총액1 (급여 진료비, 원)")
    non_benefit_total: int = Field(0, ge=0, description="비급여(100분의100) 총액 (원)")
    patient_id: Optional[UUID] = Field(
        None, description="환자 ID. 있으면 활성 산정특례 등록을 조회해 special_code보다 우선 적용"
    )
    special_code: Optional[str] = Field(
        None, description="특정기호. 산정특례(V027 등), 차상위(C001/C002). patient_id 조회 결과가 있으면 그 값으로 대체됨"
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
    graduated_fee_index: Decimal = Field(
        Decimal("0"), description="차등지수 (0=미적용, 0 초과 1 이하=차등 적용)"
    )
    procedures: list[ProcedureItem] = Field(
        default_factory=list,
        description="진료내역 목록. EDI 명세서진료내역 + 특정내역 생성에 사용",
    )

    @field_validator("graduated_fee_index")
    @classmethod
    def validate_graduated_fee_index(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("차등지수는 0 이상이어야 합니다.")
        if v > 1:
            raise ValueError("차등지수는 1 이하여야 합니다. (1 초과 청구 불가)")
        return v


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
    is_standalone: bool
    effective_date: Optional[date]
    expired_date: Optional[date]


class FeeCreate(BaseModel):
    code: str
    name: str
    category: str
    unit_price: int
    is_insured: bool = True
    is_standalone: bool = False
    insured_health: bool = True
    insured_medical_aid: bool = True
    insured_veterans: bool = False
    effective_date: Optional[date] = None
    expired_date: Optional[date] = None


class FeeUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    unit_price: Optional[int] = None
    is_insured: Optional[bool] = None
    is_standalone: Optional[bool] = None
    insured_health: Optional[bool] = None
    insured_medical_aid: Optional[bool] = None
    insured_veterans: Optional[bool] = None
    effective_date: Optional[date] = None
    expired_date: Optional[date] = None


class BillingCalcResponse(BaseModel):
    special_code: Optional[str] = None
    needs_review: bool = False
    benefit_total_1: int
    benefit_total_2: int
    copayment: int
    claim_amount: int
    upper_limit_excess: int
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
    full_price_copay_total: int
    under_full_total: int
    under_full_copay: int
    under_full_claim: int
    veterans_claim: int
    veterans_copay: int
    veterans_total: int
    under_full_veterans_claim: int
    treatment_days: Decimal
    graduated_claim: int
    graduated_index: Decimal


class BillableItemResponse(BaseModel):
    id: str
    name: str
    sub: str
    category: str
    unitPrice: float
    isInsured: bool
    requiresHyeolmyeong: bool


class LineItemInput(BaseModel):
    item_id: str
    hyeolmyeong_names: list[str] = Field(default_factory=list)


class AddLineItemsRequest(BaseModel):
    medical_record_id: str
    items: list[LineItemInput] = Field(..., min_length=1)


class ClaimLineItemResponse(BaseModel):
    id: str
    name: str
    code: str
    amount: int
    hyeolmyeong_names: list[str] | None = None

    class Config:
        from_attributes = True


class ClaimSummaryResponse(BaseModel):
    id: str
    patient_id: str
    billing_month: str
    status: str
    total_amount: int
    line_items: list[ClaimLineItemResponse]

    class Config:
        from_attributes = True


class ClaimResubmissionUpdate(BaseModel):
    """보완·추가청구 처리 — 반려(rejected)된 청구서에만 적용 가능."""
    claim_type: Literal["supplement", "addition"]
    original_receipt_no: int = Field(..., description="당초 청구명세서 접수번호")
    original_record_serial: int = Field(..., description="명일련")
    rejection_reason_code: Optional[str] = Field(
        None, max_length=2, description="심사불능사유코드 (보완청구일 때만 사용)"
    )


class ClaimResubmissionResponse(BaseModel):
    id: str
    status: str
    claim_type: str
    original_receipt_no: Optional[int] = None
    original_record_serial: Optional[int] = None
    rejection_reason_code: Optional[str] = None

    class Config:
        from_attributes = True
