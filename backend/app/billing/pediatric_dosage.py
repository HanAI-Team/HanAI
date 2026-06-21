"""소아 용량 비율 계산 모듈.

HIRA 「요양급여비용 청구방법, 심사청구서·명세서서식 및 작성요령」 기준
한방 투약 시 소아 연령별 용량 비율 산정 (검사항목 #27 소아용량 관련).

기준 (2014.1.1.부터 시행, 상기 기준의 2배 범위 내 처방 가능):
  - 만 6개월 미만:         성인용량 × 1/5  (0.2)
  - 만 6개월 이상 1세 미만: 성인용량 × 1/4  (0.25)
  - 만 1세 이상 7세 미만:   성인용량 × 1/2  (0.5)
  - 만 7세 이상 11세 미만:  성인용량 × 3/4  (0.75)
  - 만 11세 이상 (또는 생년월일 미상):성인 기준 (1.0)
"""

from datetime import date


# 연령대별 기본 비율 (성인 대비)
_RATIO_UNDER_6_MONTHS = 0.2
_RATIO_6_MONTHS_TO_1_YEAR = 0.25
_RATIO_1_TO_7_YEARS = 0.5
_RATIO_7_TO_11_YEARS = 0.75
_RATIO_ADULT = 1.0

# 2014.1.1. 고시 기준 허용되는 최대 배수 (기본 비율의 2배까지 처방 가능)
MAX_ALLOWED_MULTIPLIER = 2.0


def calculate_age_in_months(birth_date: date, reference_date: date | None = None) -> int:
    """생년월일 기준 만 나이를 '개월 수'로 계산한다.

    Args:
        birth_date: 환자 생년월일
        reference_date: 기준일 (진료일). 미지정 시 오늘 날짜 사용.

    Returns:
        만 나이 (개월 단위, 정수)
    """
    ref = reference_date or date.today()
    months = (ref.year - birth_date.year) * 12 + (ref.month - birth_date.month)
    # 일자가 안 지났으면 1개월 빼기 (만 나이 정확히 계산)
    if ref.day < birth_date.day:
        months -= 1
    return max(months, 0)


def get_pediatric_dosage_ratio(
    birth_date: date | None, reference_date: date | None = None
) -> float:
    """환자 생년월일을 받아 한방 투약 기본 용량 비율을 반환한다.

    Args:
        birth_date: 환자 생년월일. None이면 성인 기준(1.0) 반환.
        reference_date: 진료일 기준 (미지정 시 오늘).

    Returns:
        기본 용량 비율 (0.2 ~ 1.0)
    """
    if birth_date is None:
        return _RATIO_ADULT

    age_months = calculate_age_in_months(birth_date, reference_date)

    if age_months < 6:
        return _RATIO_UNDER_6_MONTHS
    elif age_months < 12:
        return _RATIO_6_MONTHS_TO_1_YEAR
    elif age_months < 7 * 12:
        return _RATIO_1_TO_7_YEARS
    elif age_months < 11 * 12:
        return _RATIO_7_TO_11_YEARS
    else:
        return _RATIO_ADULT


def get_max_allowed_ratio(birth_date: date | None, reference_date: date | None = None) -> float:
    """2014.1.1. 고시에 따라 허용되는 '최대' 용량 비율을 반환한다.

    기본 비율의 2배까지 처방 가능하므로, 한도 검증 시에는
    이 값을 사용해서 '비율 초과 여부'를 판단해야 한다.
    (성인은 애초에 1.0이 상한이므로 배수 적용 대상이 아님)
    """
    base_ratio = get_pediatric_dosage_ratio(birth_date, reference_date)
    if base_ratio >= _RATIO_ADULT:
        return _RATIO_ADULT
    return min(base_ratio * MAX_ALLOWED_MULTIPLIER, _RATIO_ADULT)
