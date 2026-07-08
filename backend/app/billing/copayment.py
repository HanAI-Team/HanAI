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


def _is_65_or_older(birth_date: Optional[date], ref: date) -> bool:
    if not birth_date:
        return False
    age = ref.year - birth_date.year
    if (ref.month, ref.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age >= 65


def _special_rate(special_code: str) -> Decimal:
    """산정특례 코드별 본인부담률.

    2026-07-07 재검증 (law.go.kr 별표4/별표4의2 원문 + HIRA 별표6 종합 코드표
    직접 대조 완료):
      - V221: 5% → 10%로 정정. "중증화상"이 아니라 별표4(희귀질환자
        산정특례 대상) 소속 "레쉬-니한증후군(E79.1)" 코드였음. 중증화상 코드는
        아래 V247/V248/V250/V305/V306 5개뿐 (별표3·별표6 Ⅲ장 원문 확인).
      - V800: 0% → 10%로 정정. 별표4의2 구분6(조기발병 알츠하이머 등)에는
        별도 면제 조항이 없고, 제5조 일반원칙(10%)이 그대로 적용됨.
        V810과 마찬가지로 10%이며, 차이는 적용기간(V800=등록일로부터 5년
        일수제한 없음 / V810=연 60일, 요건 충족 시 60일 추가)뿐.
      - V027: 삭제. "미등록 암환자" 코드였으나 HIRA 고시 제2020-191호
        (2020-09-01 시행)로 특정기호 코드 자체가 공식 폐지됨. 별표6
        종합 코드표(Ⅰ~Ⅷ장) 전체에도 더 이상 존재하지 않음이 확인됨.
        신규로 이 코드가 들어올 일은 없어야 하며, 혹시 들어오면 fallback
        (10%)이 적용된다 — 우연히 희귀난치성 요율과 같아 안전하지만,
        발생 시 반드시 사람이 확인해야 함 (개발 단계 DB 조회 결과 기존
        등록 데이터 없음, 2026-07-07 확인).
      - V191/V268/V275(뇌혈관)/V192(심장)/V273(중증외상): law.go.kr
        별표3 원문으로 이미 확정(5%)돼 있었으나 이 파일(RATES)에는 실제
        반영이 안 돼 있던 것을 뒤늦게 발견해 추가함. service.py의
        `_SPECIAL_CASE_COPAY_RATE`에는 V191/V268/V275/V192는 있었지만
        V273은 거기도 빠져 있어 같이 추가함 (2026-07-07).
    """
    RATES = {
        # V코드 — law.go.kr 별표3/별표4/별표4의2 + HIRA 별표6 원문 대조 완료
        "V193": Decimal("0.05"),  # 암
        "V191": Decimal("0.05"),  # 뇌혈관 (수술O) — 최대 30일
        "V268": Decimal("0.05"),  # 뇌혈관 (중증뇌출혈, 수술없이 급성기 입원) — 최대 30일
        "V275": Decimal("0.05"),  # 뇌경색증 (NIHSS≥5, 수술없음) — 최대 30일
        "V192": Decimal("0.05"),  # 심장 (수술/약제투여) — 최대 30일(예외 60일)
        "V273": Decimal("0.05"),  # 중증외상 (ISS≥15, 권역외상센터 입원) — 최대 30일
        "V221": Decimal("0.10"),  # 레쉬-니한증후군 (희귀질환, 별표4)
        "V247": Decimal("0.05"),  # 중증화상 (중증도기준1+체표면적기준1)
        "V248": Decimal("0.05"),  # 중증화상 (중증도기준2+체표면적기준2)
        "V250": Decimal("0.05"),  # 중증화상 (별표3 4호 상병)
        "V305": Decimal("0.05"),  # 중증화상 (2021개정 — 국소부위 3도, 외래)
        "V306": Decimal("0.05"),  # 중증화상 (2021개정 — 인체 3년내 입원수술)
        "V000": Decimal("0.00"),  # 결핵 (본인부담 면제)
        "V010": Decimal("0.00"),  # 잠복결핵감염 (본인부담 면제)
        "V800": Decimal("0.10"),  # 중증치매 (별표4의2 구분6 — 5년, 일수제한 없음)
        "V810": Decimal("0.10"),  # 중증치매 (별표4의2 구분7 — 연간 60일)
        "V811": Decimal("0.10"),  # 중증치매 (V810의 가정간호 버전)
        "V900": Decimal("0.10"),  # 극희귀질환
        "V901": Decimal("0.10"),  # 기타염색체이상질환
        "V999": Decimal("0.10"),  # 상세불명 희귀질환
        # F코드 — HIRA 별표6 Ⅷ장 원문 확인
        "F006": Decimal("0.40"),  # 신체기능저하군
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
    has_disability: bool = False                    # 장애인 등록 여부 (의료급여 2종 외래 15%→5% 경감)
    support_fund: int = 0                          # 지원금
    treatment_days: Decimal = field(default_factory=lambda: Decimal("0"))
    graduated_fee_index: Decimal = field(default_factory=lambda: Decimal("0"))
    # 추나요법 본인부담률은 코드에 따라 둘로 갈린다 (2026-07-07 확정):
    #   - 40710(단순)/40720(복잡-일반)/40730(특수·탈구) → 50%
    #   - 40721(복잡추나 중 디스크·협착증 외 근골격계 질환) → 80%
    #   (국민건강보험법 시행령 별표2 제3호 라목9)·10))
    # 기존에는 chuna_total 하나로 합산해 일괄 50%를 적용했는데, 40721이
    # 카탈로그에 없어 드러나지 않았던 버그. 40721을 카탈로그에 추가하면서
    # 함께 분리함.
    chuna_total: int = 0       # 50% 대상 추나 합계 (40710/40720/40730)
    chuna_80_total: int = 0    # 80% 대상 추나 합계 (40721)


@dataclass
class BillingResult:
    # 요양급여비용 총액
    benefit_total_1: int = 0        # 급여 총액
    benefit_total_2: int = 0        # 급여 + 비급여 총액 (진료비총액)

    # 청구 핵심 3개
    copayment: int = 0              # 본인일부부담금
    claim_amount: int = 0           # 청구액
    upper_limit_excess: int = 0     # 본인부담 상한액 초과금 (별도 계산 필요)
    chuna_copay: int = 0            # 추나 50% 대상 본인부담금
    chuna_80_copay: int = 0         # 추나 80% 대상 본인부담금
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
    senior_outpatient_copay: int = 0        # 65세 이상 노인외래 정액 (의원급)
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
            elif inp.has_disability:
                # 2종 장애인 외래: 5% 경감 (의료급여법 시행령 별표1)
                # 단, 추나요법 본인부담금은 장애인의료비 미지급 (HIRA 고시)
                # → 추나 항목은 15% 그대로, 비추나 항목만 5%로 경감하고 차액(10%)이 disability_medical_cost
                chuna_sum = inp.chuna_total + inp.chuna_80_total
                non_chuna = max(total1 - chuna_sum, 0)
                non_chuna_copay = _ceil_won(Decimal(non_chuna) * Decimal("0.05"))
                chuna_copay_ma = _ceil_won(Decimal(chuna_sum) * Decimal("0.15"))
                copay = non_chuna_copay + chuna_copay_ma
                result.disability_medical_cost = (
                    _ceil_won(Decimal(non_chuna) * Decimal("0.15")) - non_chuna_copay
                )
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

        elif special.startswith("V") or special.startswith("F"):
            # 산정특례 (V코드: 별표3/4/4의2 특정기호, F코드: 신체기능저하군 등)
            rate = _special_rate(special)
            copay = _ceil_won(Decimal(total1) * rate)
            result.special_exception_copay = copay

        else:
            # 건강보험 일반
            if inp.visit_type == VisitType.OUTPATIENT:
                if _is_65_or_older(inp.birth_date, ref_date) and total1 <= 15000:
                    # 65세 이상 노인외래 정액제 (의원급, 시행령 별표2): 15,000원 이하 → 1,500원
                    copay = min(1500, total1)
                    result.senior_outpatient_copay = copay
                else:
                    chuna_50 = inp.chuna_total
                    chuna_80 = inp.chuna_80_total
                    normal_total = max(total1 - chuna_50 - chuna_80, 0)
                    normal_copay = _ceil_won(Decimal(normal_total) * Decimal("0.30"))
                    chuna_copay = _ceil_won(Decimal(chuna_50) * Decimal("0.50"))
                    chuna_80_copay = _ceil_won(Decimal(chuna_80) * Decimal("0.80"))
                    copay = normal_copay + chuna_copay + chuna_80_copay
                    result.chuna_copay = chuna_copay
                    result.chuna_80_copay = chuna_80_copay
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
