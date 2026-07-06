"""copayment.calculate_billing() 본인부담률 산정 테스트.

건강보험 외래의 추나 분리 적용(체침 30% / 추나 50%), 의료급여, 보훈,
15세 미만 입원, 방어 로직(chuna_total > benefit_total)을 검증한다.
"""

from datetime import date

from app.billing.copayment import (
    BillingInput,
    InsuranceType,
    MedicalAidGrade,
    VisitType,
    calculate_billing,
)


def test_건강보험_외래_일반_30퍼센트():
    # chuna_total=0 → 전액 일반 30%
    result = calculate_billing(BillingInput(
        insurance_type=InsuranceType.HEALTH,
        visit_type=VisitType.OUTPATIENT,
        benefit_total=10000,
        chuna_total=0,
    ))
    assert result.health_outpatient_copay == 3000  # ceil(10000*0.30)
    assert result.copayment == 3000
    assert result.claim_amount == 7000


def test_건강보험_외래_추나만_50퍼센트():
    # benefit_total == chuna_total → 전액 추나 50%
    result = calculate_billing(BillingInput(
        insurance_type=InsuranceType.HEALTH,
        visit_type=VisitType.OUTPATIENT,
        benefit_total=20060,
        chuna_total=20060,
    ))
    assert result.health_outpatient_copay == 10030  # ceil(20060*0.50)
    assert result.copayment == 10030
    assert result.claim_amount == 10030


def test_건강보험_외래_혼재_체침과_추나_합산():
    # 체침 6,260원(30%) + 추나 20,060원(50%) 합산
    result = calculate_billing(BillingInput(
        insurance_type=InsuranceType.HEALTH,
        visit_type=VisitType.OUTPATIENT,
        benefit_total=6260 + 20060,
        chuna_total=20060,
    ))
    expected_normal_copay = 1878   # ceil(6260*0.30)
    expected_chuna_copay = 10030   # ceil(20060*0.50)
    assert result.health_outpatient_copay == expected_normal_copay + expected_chuna_copay
    assert result.copayment == 11908
    assert result.claim_amount == 26320 - 11908


def test_의료급여_1종_외래_정액():
    result = calculate_billing(BillingInput(
        insurance_type=InsuranceType.MEDICAL_AID,
        visit_type=VisitType.OUTPATIENT,
        benefit_total=15000,
        medical_aid_grade=MedicalAidGrade.GRADE_1,
    ))
    assert result.medical_aid_outpatient_copay == 1000
    assert result.copayment == 1000


def test_의료급여_2종_외래_15퍼센트():
    result = calculate_billing(BillingInput(
        insurance_type=InsuranceType.MEDICAL_AID,
        visit_type=VisitType.OUTPATIENT,
        benefit_total=10000,
        medical_aid_grade=MedicalAidGrade.GRADE_2,
    ))
    assert result.medical_aid_outpatient_copay == 1500  # ceil(10000*0.15)
    assert result.copayment == 1500


def test_보훈_본인부담_없음_전액청구():
    result = calculate_billing(BillingInput(
        insurance_type=InsuranceType.VETERANS,
        visit_type=VisitType.OUTPATIENT,
        benefit_total=18000,
    ))
    assert result.veterans_copay == 0
    assert result.copayment == 0
    assert result.veterans_claim == 18000
    assert result.claim_amount == 18000


def test_15세미만_입원_5퍼센트():
    result = calculate_billing(BillingInput(
        insurance_type=InsuranceType.HEALTH,
        visit_type=VisitType.INPATIENT,
        benefit_total=20000,
        birth_date=date(2015, 1, 1),
        treatment_date=date(2026, 6, 1),  # 기준일 만 11세
    ))
    assert result.under_15_inpatient_copay == 1000  # ceil(20000*0.05)
    assert result.health_inpatient_copay == 0
    assert result.copayment == 1000


def test_노인외래_15000이하_1500원_정액():
    # 65세 이상, 건강보험 외래, 총진료비 ≤ 15,000원 → 1,500원 정액
    result = calculate_billing(BillingInput(
        insurance_type=InsuranceType.HEALTH,
        visit_type=VisitType.OUTPATIENT,
        benefit_total=12000,
        birth_date=date(1960, 1, 1),
        treatment_date=date(2026, 7, 7),  # 만 66세
    ))
    assert result.senior_outpatient_copay == 1500
    assert result.health_outpatient_copay == 0
    assert result.copayment == 1500
    assert result.claim_amount == 10500


def test_노인외래_15000초과_일반30퍼센트():
    # 65세 이상이어도 15,000원 초과이면 일반 30% 적용
    result = calculate_billing(BillingInput(
        insurance_type=InsuranceType.HEALTH,
        visit_type=VisitType.OUTPATIENT,
        benefit_total=20000,
        birth_date=date(1960, 1, 1),
        treatment_date=date(2026, 7, 7),  # 만 66세
    ))
    assert result.senior_outpatient_copay == 0
    assert result.health_outpatient_copay == 6000  # ceil(20000*0.30)
    assert result.copayment == 6000


def test_노인외래_정확히_15000원_정액적용():
    # 경계값: 총진료비 = 15,000원 정확히 → 1,500원 정액
    result = calculate_billing(BillingInput(
        insurance_type=InsuranceType.HEALTH,
        visit_type=VisitType.OUTPATIENT,
        benefit_total=15000,
        birth_date=date(1960, 1, 1),
        treatment_date=date(2026, 7, 7),
    ))
    assert result.senior_outpatient_copay == 1500
    assert result.copayment == 1500


def test_노인외래_진료비가_정액보다_적으면_진료비만():
    # 총진료비 1,000원이면 1,500원 정액 적용 불가 → 1,000원으로 캡
    result = calculate_billing(BillingInput(
        insurance_type=InsuranceType.HEALTH,
        visit_type=VisitType.OUTPATIENT,
        benefit_total=1000,
        birth_date=date(1960, 1, 1),
        treatment_date=date(2026, 7, 7),
    ))
    assert result.senior_outpatient_copay == 1000
    assert result.copayment == 1000
    assert result.claim_amount == 0


def test_64세는_노인정액제_미적용():
    # 만 64세 → 일반 30% 적용
    result = calculate_billing(BillingInput(
        insurance_type=InsuranceType.HEALTH,
        visit_type=VisitType.OUTPATIENT,
        benefit_total=12000,
        birth_date=date(1962, 7, 8),       # 2026-07-07 기준 아직 만 63세
        treatment_date=date(2026, 7, 7),
    ))
    assert result.senior_outpatient_copay == 0
    assert result.health_outpatient_copay == 3600  # ceil(12000*0.30)
    assert result.copayment == 3600


def test_65세이상_산정특례_있으면_산정특례_우선():
    # V193(암 5%)와 65세 이상이 겹치면 산정특례 코드 분기가 먼저 처리되어 5% 적용
    result = calculate_billing(BillingInput(
        insurance_type=InsuranceType.HEALTH,
        visit_type=VisitType.OUTPATIENT,
        benefit_total=12000,
        special_code="V193",
        birth_date=date(1960, 1, 1),
        treatment_date=date(2026, 7, 7),
    ))
    assert result.special_exception_copay == 600  # ceil(12000*0.05)
    assert result.senior_outpatient_copay == 0
    assert result.copayment == 600


def test_chuna_total이_benefit_total보다_큰_경우_normal_total_음수방어():
    # chuna_total(20060) > benefit_total(5000) → normal_total은 음수가 아닌 0으로 방어
    result = calculate_billing(BillingInput(
        insurance_type=InsuranceType.HEALTH,
        visit_type=VisitType.OUTPATIENT,
        benefit_total=5000,
        chuna_total=20060,
    ))
    expected_chuna_copay = 10030  # ceil(20060*0.50)
    assert result.health_outpatient_copay == expected_chuna_copay  # normal_copay=0 기여
    assert result.copayment == expected_chuna_copay
    # claim_amount도 음수 방어로 0
    assert result.claim_amount == 0
