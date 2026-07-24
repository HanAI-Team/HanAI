import re
from datetime import date, datetime
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
    has_disability: bool = Field(False, description="장애인 등록 여부 (의료급여 2종 외래 15%→5% 경감)")
    support_fund: int = Field(0, ge=0, description="지원금 (원)")
    treatment_days: Decimal = Field(Decimal("0"), description="진료(조제)일수")
    graduated_fee_index: Decimal = Field(
        Decimal("0"), description="차등지수 (0=미적용, 0 초과 1 이하=차등 적용)"
    )
    exam_fee: int = Field(0, ge=0, description="진찰료 (원). 차등수가청구액 계산에 필요")
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


class MaterialItem(BaseModel):
    code: str
    name: str
    category: Optional[str] = None
    unit_price: int
    effective_date: Optional[date]
    expired_date: Optional[date]

    class Config:
        from_attributes = True


class MaterialCreate(BaseModel):
    code: str
    name: str
    category: Optional[str] = None
    unit_price: int
    effective_date: Optional[date] = None
    expired_date: Optional[date] = None


class MaterialUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    unit_price: Optional[int] = None
    effective_date: Optional[date] = None
    expired_date: Optional[date] = None


class MaterialPurchaseRecordItem(BaseModel):
    id: UUID
    record_type: Literal["purchase", "compound"]
    item_name: str
    item_code: Optional[str] = None
    spec: Optional[str] = None
    quantity: Decimal
    unit_price: int
    amount: int
    supplier_name: Optional[str] = None
    transaction_date: date
    reported: bool
    reported_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MaterialPurchaseRecordCreate(BaseModel):
    record_type: Literal["purchase", "compound"]
    item_name: str
    item_code: Optional[str] = None
    spec: Optional[str] = None
    quantity: Decimal = Decimal("1")
    unit_price: int = 0
    amount: int = 0
    supplier_name: Optional[str] = None
    transaction_date: date


class MaterialPurchaseRecordUpdate(BaseModel):
    item_name: Optional[str] = None
    item_code: Optional[str] = None
    spec: Optional[str] = None
    quantity: Optional[Decimal] = None
    unit_price: Optional[int] = None
    amount: Optional[int] = None
    supplier_name: Optional[str] = None
    transaction_date: Optional[date] = None


class MissingDeclarationItem(BaseModel):
    code: str
    name: str
    claim_count: int
    total_qty: Decimal


class MissingDeclarationCheckResponse(BaseModel):
    year: int
    month: int
    items: list[MissingDeclarationItem]


class DoctorWorkDaysItem(BaseModel):
    id: int
    claim_period_year: int
    claim_period_month: int
    doctor_birth_date: str
    work_days: int


class DoctorWorkDaysCreate(BaseModel):
    claim_period_year: int = Field(..., ge=2000, le=2100)
    claim_period_month: int = Field(..., ge=1, le=12)
    doctor_birth_date: str = Field(
        ..., min_length=6, max_length=6, description="의사 생년월일 YYMMDD (6자리)"
    )
    work_days: int = Field(..., ge=0, le=31, description="해당 월 실제 진료일수")

    @field_validator("doctor_birth_date")
    @classmethod
    def validate_doctor_birth_date(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("doctor_birth_date는 숫자 6자리(YYMMDD)여야 합니다.")
        return v


class DoctorWorkDaysUpdate(BaseModel):
    doctor_birth_date: Optional[str] = Field(None, min_length=6, max_length=6)
    work_days: Optional[int] = Field(None, ge=0, le=31)

    @field_validator("doctor_birth_date")
    @classmethod
    def validate_doctor_birth_date(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.isdigit():
            raise ValueError("doctor_birth_date는 숫자 6자리(YYMMDD)여야 합니다.")
        return v


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
    acupoint_codes: list[str] = Field(
        default_factory=list,
        description="경혈 코드 목록(AcupuncturePoint.code). requiresHyeolmyeong 항목일 때만 사용",
    )
    is_non_benefit: bool = False


class AddLineItemsRequest(BaseModel):
    medical_record_id: str
    items: list[LineItemInput] = Field(..., min_length=1)
    visit_type: Literal["외래", "입원"] = Field("외래", description="외래 | 입원 (VisitType enum과 일치)")


class AcupointRef(BaseModel):
    code: str
    korean_name: str

    class Config:
        from_attributes = True


class ClaimLineItemResponse(BaseModel):
    id: str
    name: str
    code: str
    amount: int
    acupoints: list[AcupointRef] = Field(default_factory=list)
    is_non_benefit: bool = False
    performed_by_doctor_id: str | None = None

    class Config:
        from_attributes = True


class HospitalDoctorItem(BaseModel):
    id: str
    name: str
    license_kind: str | None = None
    license_number: str | None = None


class LineItemDoctorUpdate(BaseModel):
    performed_by_doctor_id: str | None = None


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


class NeedsReviewClaimItem(BaseModel):
    id: UUID
    patient_id: UUID
    patient_name: str
    claim_period_year: int
    claim_period_month: int
    special_case_review_reason: str
    status: str
    total_amount: int
    created_at: datetime

    class Config:
        from_attributes = True


class NeedsReviewClaimsResponse(BaseModel):
    total: int
    items: list[NeedsReviewClaimItem]


class ClaimRejectionCodeResponse(BaseModel):
    category: str
    code: str
    detail_code: str
    description: str

    class Config:
        from_attributes = True


class DrugMasterResponse(BaseModel):
    product_code: str
    product_name: str
    ingredient_code: Optional[str]
    ingredient_name: Optional[str]
    company_name: Optional[str]
    spec: Optional[str]
    unit: Optional[str]
    unit_price: int
    administration_route: Optional[str]
    classification_code: Optional[str]
    is_prescription: Optional[bool]
    effective_date: Optional[date]

    class Config:
        from_attributes = True


class DrugMasterCreate(BaseModel):
    product_code: str
    product_name: str
    ingredient_code: Optional[str] = None
    ingredient_name: Optional[str] = None
    company_name: Optional[str] = None
    spec: Optional[str] = None
    unit: Optional[str] = None
    unit_price: int
    administration_route: Optional[str] = None
    classification_code: Optional[str] = None
    is_prescription: Optional[bool] = None
    effective_date: Optional[date] = None


class DrugMasterUpdate(BaseModel):
    product_name: Optional[str] = None
    ingredient_code: Optional[str] = None
    ingredient_name: Optional[str] = None
    company_name: Optional[str] = None
    spec: Optional[str] = None
    unit: Optional[str] = None
    unit_price: Optional[int] = None
    administration_route: Optional[str] = None
    classification_code: Optional[str] = None
    is_prescription: Optional[bool] = None
    effective_date: Optional[date] = None


class ClaimRejectionCodeCreate(BaseModel):
    category: str
    code: str
    detail_code: str = ""
    description: str


class ClaimRejectionCodeUpdate(BaseModel):
    description: Optional[str] = None


class StatementProcedureRow(BaseModel):
    """요양급여비용명세서(한방외래, 별지18호/GI013) 진료내역 한 줄. 같은
    (hang, mok, code) 청구항목을 합산한 결과."""
    hang: str
    mok: str
    code: str
    name: str
    unit_price: int
    count: int
    amount: int
    is_non_benefit: bool
    copay_rate_label: Optional[Literal["A", "B"]] = Field(
        None, description="A=추나 100분의50, B=추나 100분의80. 그 외 일반 항목은 None"
    )


class ClaimStatementResponse(BaseModel):
    """요양급여비용명세서(한방외래, 별지18호/GI013) 출력용 데이터."""
    hospital_name: str
    institution_code: str
    patient_name: str
    birth_masked: str
    disease_names: list[str]
    special_code: Optional[str]
    doctor_name: str
    license_type: str
    license_no: str
    visit_dates: list[str]
    visit_count: int

    procedures: list[StatementProcedureRow]

    # 심사내역 (13~26번 및 소계/가산율/비급여총액)
    subtotal: int
    surcharge_rate: float
    benefit_total_1: int
    copayment: int
    support_fund: int
    disability_medical_cost: int
    claim_amount: int
    upper_limit_excess: int
    non_benefit_total: int
    benefit_total_2: int
    veterans_claim: int
    full_price_copay_total: int
    veterans_copay: int
    under_full_total: int
    under_full_copay: int
    under_full_claim: int
    under_full_veterans_claim: int


class ClaimPrescriptionResponse(BaseModel):
    """처방전(의료법 시행규칙 별지 제9호서식) 출력용 데이터.

    이 앱은 환자별 약품 처방(품명/코드/투약량/투여횟수/투약일수)을 입력받는
    기능이 아직 없어, 서식의 상단부(요양기관·환자·처방의료인 정보)만 자동
    채우고 처방 의약품 테이블은 빈칸으로 출력해 수기로 작성하게 한다.
    """
    hospital_name: str
    institution_code: str
    hospital_phone: str
    issue_date: str          # 발급 연월일 YYYY-MM-DD
    issue_no: str            # 발급번호 (청구번호로 대체 — 별도 처방전 발급 일련번호 체계 없음)
    patient_name: str
    patient_birth_masked: str
    disease_names: list[str]
    doctor_name: str
    license_type: str
    license_no: str


class ClaimApprovalUpdateRequest(BaseModel):
    approval_no: str | None = None


class ClaimPaymentCreateRequest(BaseModel):
    method: Literal["cash", "card", "transfer"]
    amount: int = Field(..., gt=0)


class ClaimPaymentResponse(BaseModel):
    id: UUID
    claim_id: UUID
    patient_name: str
    method: Literal["cash", "card", "transfer"]
    claim_amount: int  # 청구액 (Claim.claim_amount, 참고용)
    amount: int         # 실제 수납액
    paid_at: str
    processed_by_name: str


class ClaimBillingAgentUpdateRequest(BaseModel):
    billing_agent_code: str | None = None
    billing_agent_name: str | None = None


class ClaimReviewResultResponse(BaseModel):
    id: UUID
    claim_id: UUID | None = None
    receipt_number: str
    review_type: str
    result_code: str
    original_amount: int
    approved_amount: int
    reduced_amount: int
    reduce_reason: str | None = None
    review_date: date
    received_at: datetime
    raw_content: str | None = None

    class Config:
        from_attributes = True


class ClaimPaymentListResponse(BaseModel):
    total: int
    page: int
    size: int
    items: list[ClaimPaymentResponse]


class ClaimPaymentSummaryResponse(BaseModel):
    today_total: int
    month_total: int
    cash_ratio: float   # 0~100, 필터링된 범위 내 현금 비율
    card_ratio: float   # 0~100, 필터링된 범위 내 카드 비율


class QuickFeeItemResponse(BaseModel):
    code: str
    name: str
    category: str
    unit_price: int


class QuickFeeItemsResponse(BaseModel):
    categories: list[str]                              # FeeMaster에 실제 존재하는 카테고리 목록
    favorites: list[QuickFeeItemResponse]               # "자주" 탭 — 최근 사용빈도 상위 N개
    by_category: dict[str, list[QuickFeeItemResponse]]  # 카테고리별 전체 목록


class CheckoutPreviewLineItem(BaseModel):
    code: str
    qty: float = 1
    days: int = 1


class CheckoutPreviewRequest(BaseModel):
    patient_id: UUID
    line_items: list[CheckoutPreviewLineItem]


class CheckoutPreviewResponse(BaseModel):
    total_amount: int          # 총진료비
    patient_copay: int         # 본인부담금
    claim_amount: int          # 청구액
    special_code: str | None   # 산정특례 코드 (있으면 산정특례 적용)


class ClaimReviewResultListResponse(BaseModel):
    total: int
    page: int
    size: int
    items: list[ClaimReviewResultResponse]


class ClaimReviewResultUploadResponse(BaseModel):
    inserted: int
    skipped: int


class SpecialCaseCodeItem(BaseModel):
    """산정특례 특정기호 선택지 (등록 화면 드롭다운용)."""
    code: str
    category: str
    description: str


_REGISTRATION_NUMBER_PATTERN = re.compile(r"^[\d-]+$")


def _validate_special_case_registration_number(v: Optional[str]) -> Optional[str]:
    """MT014(9(20), 숫자 최대 20자리) 최소 형식 검증.

    HIRA 원문상 자릿수는 보험유형·등록유형(일반/틀니/임플란트)에 따라
    10~18자리로 갈리지만 이 구분 자체가 시스템에 모델링돼 있지 않아 정확한
    자릿수는 강제하지 않는다. 다만 이 프로젝트의 기존 예시값(모델 주석
    "01-24-00012345", 사전승인번호 "1-26-00000001")이 하이픈 구분자를 포함하고
    있어, 숫자만 허용하면 기존 표기 관례와 충돌한다 — 숫자+하이픈을 허용하고,
    하이픈을 제외한 실제 자릿수만 20자 이하로 제한한다.
    """
    if not v:
        return v
    if not _REGISTRATION_NUMBER_PATTERN.fullmatch(v):
        raise ValueError("등록번호는 숫자와 하이픈(-)만 입력할 수 있습니다.")
    if len(v.replace("-", "")) > 20:
        raise ValueError("등록번호는 하이픈을 제외한 자릿수가 최대 20자를 넘을 수 없습니다.")
    return v


class SpecialCaseRegistrationCreate(BaseModel):
    special_code: str = Field(..., max_length=4, description="특정기호 (예: V193=암)")
    category: str = Field(..., max_length=20, description="암 / 결핵 / 뇌혈관 / 심장 / 신체기능저하군 등")
    registered_disease_code: Optional[str] = Field(None, max_length=10, description="등록 상병코드 (KCD/ICD)")
    disease_name: Optional[str] = Field(None, max_length=100, description="KCD 코드 없는 희귀질환 등의 실제 상병명 (MT028용)")
    registration_number: Optional[str] = Field(None, max_length=20, description="건보공단 발급 산정특례 등록번호 (MT014용)")
    prior_approval_number: Optional[str] = Field(None, max_length=30, description="V810 전용 사전승인번호")
    registered_at: date
    expires_at: Optional[date] = None

    @field_validator("registration_number", "prior_approval_number")
    @classmethod
    def validate_registration_number(cls, v: Optional[str]) -> Optional[str]:
        return _validate_special_case_registration_number(v)


class SpecialCaseRegistrationUpdate(BaseModel):
    category: Optional[str] = Field(None, max_length=20)
    registered_disease_code: Optional[str] = Field(None, max_length=10)
    disease_name: Optional[str] = Field(None, max_length=100)
    registration_number: Optional[str] = Field(None, max_length=20)
    prior_approval_number: Optional[str] = Field(None, max_length=30)
    registered_at: Optional[date] = None
    expires_at: Optional[date] = None

    @field_validator("registration_number", "prior_approval_number")
    @classmethod
    def validate_registration_number(cls, v: Optional[str]) -> Optional[str]:
        return _validate_special_case_registration_number(v)


class SpecialCaseRegistrationResponse(BaseModel):
    id: UUID
    patient_id: UUID
    special_code: str
    category: str
    registered_disease_code: Optional[str] = None
    disease_name: Optional[str] = None
    registration_number: Optional[str] = None
    prior_approval_number: Optional[str] = None
    registered_at: date
    expires_at: Optional[date] = None
    status: str

    class Config:
        from_attributes = True


class SpecialCaseRegistrationListResponse(BaseModel):
    items: list[SpecialCaseRegistrationResponse]
