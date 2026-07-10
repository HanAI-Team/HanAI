"""추나요법 본인부담률 50%/80% 분리 계산 테스트 (2026-07-07 신규).

40721(복잡추나 중 디스크·협착증 외 근골격계 질환)이 카탈로그에 없어
80% 요율이 아예 적용될 수 없던 버그를 수정하면서 추가한 테스트.
"""

from app.billing.copayment import (
    BillingInput,
    InsuranceType,
    VisitType,
    calculate_billing,
)


def test_추나_50퍼센트_단독():
    # 40710/40720/40730 (단순/복잡/특수) — 50%. chuna_copay는 절사 전 세부값을
    # 그대로 보여주는 내역 필드라 ceil(44450*0.50)=22225 그대로지만, 본인일부
    # 부담금 총액(copayment)은 외래 100원 미만 절사 → 22200
    result = calculate_billing(BillingInput(
        insurance_type=InsuranceType.HEALTH,
        visit_type=VisitType.OUTPATIENT,
        benefit_total=44450,
        chuna_total=44450,
        chuna_80_total=0,
    ))
    assert result.chuna_copay == 22225  # ceil(44450*0.50)
    assert result.chuna_80_copay == 0
    assert result.copayment == 22200


def test_추나_80퍼센트_단독():
    # 40721 (복잡추나 중 디스크·협착증 외 근골격계 질환) — 80%.
    # ceil(44450*0.80)=35560 → 외래 100원 미만 절사 → 35500
    result = calculate_billing(BillingInput(
        insurance_type=InsuranceType.HEALTH,
        visit_type=VisitType.OUTPATIENT,
        benefit_total=44450,
        chuna_total=0,
        chuna_80_total=44450,
    ))
    assert result.chuna_copay == 0
    assert result.chuna_80_copay == 35560  # ceil(44450*0.80)
    assert result.copayment == 35500


def test_추나_50퍼센트와_80퍼센트_동시_청구():
    # 같은 날 40720(50%)과 40721(80%)을 같이 시행한 경우 (재시행 등).
    # 22225+35560=57785 → 외래 100원 미만 절사 → 57700
    result = calculate_billing(BillingInput(
        insurance_type=InsuranceType.HEALTH,
        visit_type=VisitType.OUTPATIENT,
        benefit_total=44450 + 44450,
        chuna_total=44450,
        chuna_80_total=44450,
    ))
    assert result.chuna_copay == 22225   # ceil(44450*0.50)
    assert result.chuna_80_copay == 35560   # ceil(44450*0.80)
    assert result.copayment == 57700


def test_추나와_일반진료_혼재():
    # 일반 진료(30%) + 추나 50% + 추나 80% 셋 다 섞인 경우.
    # 3000+13165+35560=51725 → 외래 100원 미만 절사 → 51700
    normal = 10000
    chuna_50 = 26330   # 40710 단순추나
    chuna_80 = 44450   # 40721
    result = calculate_billing(BillingInput(
        insurance_type=InsuranceType.HEALTH,
        visit_type=VisitType.OUTPATIENT,
        benefit_total=normal + chuna_50 + chuna_80,
        chuna_total=chuna_50,
        chuna_80_total=chuna_80,
    ))
    assert result.copayment == 51700


def test_추나_없으면_기존과_동일하게_동작():
    # 회귀 방지: chuna_80_total 필드 추가가 기존 동작을 안 깨는지 확인
    result = calculate_billing(BillingInput(
        insurance_type=InsuranceType.HEALTH,
        visit_type=VisitType.OUTPATIENT,
        benefit_total=10000,
    ))
    assert result.chuna_copay == 0
    assert result.chuna_80_copay == 0
    assert result.copayment == 3000  # ceil(10000*0.30), 추나 없는 일반 진료
