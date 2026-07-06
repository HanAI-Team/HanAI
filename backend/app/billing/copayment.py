"""본인부담금 산정 엔진.

HIRA 「요양급여비용 청구방법, 심사청구서·명세서서식 및 작성요령」 기준.
한방 의원(의치과 및 한방, 수록사양 U1) 외래·입원 청구에 사용.

보험자종별구분: 4=건강보험, 5=의료급여, 7=보훈
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_UP, Decimal
from enum import Enum
from typing import Optional


class InsuranceType(str, Enum):
    HEALTH = "4"       # 건강보험
    MEDICAL_AID = "5"  # 의료급여
    VETERANS = "7"     # 보훈


class VisitType(str, Enum):
    OUTPATIENT = "외래"
    INPATIENT = "입원"


class MedicalAidGrade(str, Enum):
    GRADE_1 = "1"  # 의료급여 1종
    GRADE_2 = "2"  # 의료급여 2종


def _ceil_won(amount: Decimal) -> int:
    """원 단위 올림 (심평원 계산 기준)."""
    return int(amount.quantize(Decimal("1"), rounding=ROUND_UP))


def _is_under_15(birth_date: Optional[date], ref: date) -> bool:
    if not birth_date:
        return False
    age = ref.year - birth_date.year
    if (ref.month, ref.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age < 15


def _special_rate(special_code: str) -> Decimal:
    """산정특례 코드별 본인부담률."""
    # V193: 암, V027: 희귀난치, V221: 중증화상 등
    # 암·희귀난치 5~10%, 나머지 V코드는 10% 기본
    RATES = {
        "V193": Decimal("0.05"),  # 암
        "V027": Decimal("0.10"),  # 희귀난치성
        "V221": Decimal("0.05"),  # 중증화상
        "V000": Decimal("0.00"),  # 결핵 (본인부담 면제)
        "V010": Decimal("0.00"),  # 잠복결핵감염 (본인부담 면제)
    }
    prefix = special_code[:4] if len(special_code) >= 4 else special_code
    return RATES.get(prefix, Decimal("0.10"))


@dataclass
class BillingInput:
    insurance_type: InsuranceType 
    visit_type: VisitType
    benefit_total: int                              # 요양급여비용 총액1 (원)
    non_benefit_total: int = 0                      # 비급여(100분의100) 총액
    special_code: Optional[str] = None             # 특정기호 (산정특례·차상위 등)
    medical_aid_grade: Optional[MedicalAidGrade] = None
    birth_date: Optional[date] = None
    treatment_date: Optional[date] = None           # 진료일 (15세 이하 판단 기준)
    work_injury: bool = False                       # 공상 여부
    disability_medical_cost: int = 0               # 장애인의료비 (의료급여)
    support_fund: int = 0                          # 지원금
    treatment_days: Decimal = field(default_factory=lambda: Decimal("0"))
    graduated_fee_index: Decimal = field(default_factory=lambda: Decimal("0"))
    chuna_total : int = 0

@dataclass
class BillingResult:
    # 요양급여비용 총액
    benefit_total_1: int = 0        # 급여 총액
    benefit_total_2: int = 0        # 급여 + 비급여 총액 (진료비총액)

    # 청구 핵심 3개
    copayment: int = 0              # 본인일부부담금
    claim_amount: int = 0           # 청구액
    upper_limit_excess: int = 0     # 본인부담 상한액 초과금 (별도 계산 필요)
    chuna_copay: int = 0
    # 유형별 본인일부부담금 (해당하는 항목만 값, 나머지 0)
    health_outpatient_copay: int = 0        # 건강보험 외래
    health_inpatient_copay: int = 0         # 건강보험 입원
    medical_aid_outpatient_copay: int = 0   # 의료급여 외래
    medical_aid_inpatient_copay: int = 0    # 의료급여 입원
    near_poverty_1_copay: int = 0           # 차상위1종
    near_poverty_2_outpatient_copay: int = 0  # 차상위2종 외래
    near_poverty_2_inpatient_copay: int = 0   # 차상위2종 입원
    special_exception_copay: int = 0        # 산정특례
    work_injury_copay: int = 0              # 공상
    under_15_inpatient_copay: int = 0       # 15세 이하 입원
    disability_medical_cost: int = 0        # 장애인의료비 (의료급여)
    support_fund: int = 0                   # 지원금

    # 100분의100 (비급여 본인부담)
    full_price_copay_total: int = 0         # 건강보험(의료급여) 100분의100 본인부담금총액

    # 100분의100미만 (급여 부분)
    under_full_total: int = 0               # 100분의100미만 총액
    under_full_copay: int = 0              # 100분의100미만 본인일부부담금
    under_full_claim: int = 0              # 100분의100미만 청구액

    # 보훈
    veterans_claim: int = 0                # 보훈청구액
    veterans_copay: int = 0               # 보훈 본인일부부담금
    veterans_total: int = 0               # 보훈위탁진료 진료비총액
    under_full_veterans_claim: int = 0     # 100분의100미만 보훈청구액

    # 차등수가
    treatment_days: Decimal = field(default_factory=lambda: Decimal("0"))
    graduated_claim: int = 0              # 차등수가청구액
    graduated_index: Decimal = field(default_factory=lambda: Decimal("0"))


def calculate_billing(inp: BillingInput) -> BillingResult:
    """30개 청구 필드를 산출한다."""
    result = BillingResult()
    total1 = inp.benefit_total
    non_benefit = inp.non_benefit_total
    ref_date = inp.treatment_date or date.today()

    result.benefit_total_1 = total1
    result.benefit_total_2 = total1 + non_benefit
    result.full_price_copay_total = non_benefit
    result.under_full_total = total1
    result.disability_medical_cost = inp.disability_medical_cost
    result.support_fund = inp.support_fund
    result.treatment_days = inp.treatment_days
    result.graduated_index = inp.graduated_fee_index

    copay = 0

    if inp.insurance_type == InsuranceType.VETERANS:
        # 보훈: 전액 보훈처 청구, 환자 본인부담 없음
        result.veterans_claim = total1
        result.veterans_copay = 0
        result.veterans_total = result.benefit_total_2
        result.under_full_veterans_claim = total1
        copay = 0

    elif inp.work_injury:
        # 공상(산재): 본인부담 없음
        result.work_injury_copay = 0
        copay = 0

    elif inp.insurance_type == InsuranceType.MEDICAL_AID:
        if inp.visit_type == VisitType.OUTPATIENT:
            if inp.medical_aid_grade == MedicalAidGrade.GRADE_1:
                copay = 1000  # 1종 외래: 1,000원 정액 (의원급)
            else:
                copay = _ceil_won(Decimal(total1) * Decimal("0.15"))
            result.medical_aid_outpatient_copay = copay
        else:
            if inp.medical_aid_grade == MedicalAidGrade.GRADE_1:
                copay = 0     # 1종 입원: 전액 급여
            else:
                copay = _ceil_won(Decimal(total1) * Decimal("0.10"))
            result.medical_aid_inpatient_copay = copay

    elif inp.insurance_type == InsuranceType.HEALTH:
        special = inp.special_code or ""

        if special.startswith("C001"):
            # 차상위1종: 외래 2,000원 정액 (의원급)
            copay = 2000
            result.near_poverty_1_copay = copay

        elif special.startswith("C002"):
            if inp.visit_type == VisitType.OUTPATIENT:
                copay = _ceil_won(Decimal(total1) * Decimal("0.15"))
                result.near_poverty_2_outpatient_copay = copay
            else:
                copay = _ceil_won(Decimal(total1) * Decimal("0.10"))
                result.near_poverty_2_inpatient_copay = copay

        elif special.startswith("V"):
            # 산정특례
            rate = _special_rate(special)
            copay = _ceil_won(Decimal(total1) * rate)
            result.special_exception_copay = copay

        else:
            # 건강보험 일반
            if inp.visit_type == VisitType.OUTPATIENT:
                normal_total = max(total1 - inp.chuna_total, 0)
                normal_copay = _ceil_won(Decimal(normal_total) * Decimal("0.30"))
                chuna_copay  = _ceil_won(Decimal(inp.chuna_total) * Decimal("0.50"))
                copay = normal_copay + chuna_copay
                result.health_outpatient_copay = copay
            else:
                if _is_under_15(inp.birth_date, ref_date):
                    # 15세 미만 입원: 5%
                    copay = _ceil_won(Decimal(total1) * Decimal("0.05"))
                    result.under_15_inpatient_copay = copay
                else:
                    copay = _ceil_won(Decimal(total1) * Decimal("0.20"))
                    result.health_inpatient_copay = copay

    result.copayment = copay
    result.claim_amount = max(total1 - copay, 0)
    result.under_full_copay = copay
    result.under_full_claim = result.claim_amount

    # 차등수가청구액: 차등지수가 있으면 청구액에 지수 적용
    if inp.graduated_fee_index > 0:
        result.graduated_claim = _ceil_won(
            Decimal(result.claim_amount) * inp.graduated_fee_index
        )
    else:
        result.graduated_claim = result.claim_amount

    return result
