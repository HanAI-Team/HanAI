"""
validate_notice_rules() 순수 함수 단위 테스트.

DB·HTTP 레이어 없이 notice_rules.py 로직만 직접 검증한다.
service 레이어를 통한 통합 테스트는 test_notice_rules.py 참조.
"""

from app.billing.notice_rules import validate_notice_rules


def _physio_item(is_holiday: bool, surcharge_applied: bool = False, category: str = "전기/온열") -> dict:
    return {
        "code": "40700",
        "name": "온냉경락요법(온열)",
        "category": category,
        "is_holiday": is_holiday,
        "metadata": {"holiday_surcharge_applied": surcharge_applied} if surcharge_applied else {},
    }


def test_holiday_physio_전기온열_공휴일_가산미적용_경고발동():
    """전기/온열 카테고리 + 공휴일 + 가산 미적용 → NOTICE_2008_124_HOLIDAY_PHYSIOTHERAPY WARN 발동."""
    results = validate_notice_rules(procedures=[_physio_item(is_holiday=True)])
    rule_ids = [r["rule_id"] for r in results]
    assert "NOTICE_2008_124_HOLIDAY_PHYSIOTHERAPY" in rule_ids


def test_holiday_physio_전기온열_공휴일_가산적용_경고없음():
    """가산이 이미 적용된 경우 경고 없음."""
    results = validate_notice_rules(procedures=[_physio_item(is_holiday=True, surcharge_applied=True)])
    rule_ids = [r["rule_id"] for r in results]
    assert "NOTICE_2008_124_HOLIDAY_PHYSIOTHERAPY" not in rule_ids


def test_holiday_physio_전기온열_비공휴일_경고없음():
    """공휴일이 아니면 전기/온열이라도 경고 없음."""
    results = validate_notice_rules(procedures=[_physio_item(is_holiday=False)])
    rule_ids = [r["rule_id"] for r in results]
    assert "NOTICE_2008_124_HOLIDAY_PHYSIOTHERAPY" not in rule_ids


def test_holiday_physio_침술_공휴일_경고없음():
    """침술 카테고리는 공휴일이어도 물리치료 가산 경고 대상이 아님."""
    results = validate_notice_rules(procedures=[_physio_item(is_holiday=True, category="침술")])
    rule_ids = [r["rule_id"] for r in results]
    assert "NOTICE_2008_124_HOLIDAY_PHYSIOTHERAPY" not in rule_ids


def test_보훈국비_실제저장값_veterans_MT038_JT019_차단():
    """service.py의 _INSURANCE_MAP이 실제로 저장하는 값 "veterans"로 판정해야 한다."""
    results = validate_notice_rules(patient={"insurance_type": "veterans"})
    rule_ids = [r["rule_id"] for r in results]
    assert "NOTICE_2012_117_MT038" in rule_ids
    assert "NOTICE_2012_117_JT019" in rule_ids
