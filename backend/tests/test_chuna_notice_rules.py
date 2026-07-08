"""추나요법 연간 20회 / 1일 18명 한도 WARN 검증 테스트 (2026-07-07 신규).

validate_notice_rules()는 순수 함수라 DB 조회는 호출부(service.create_claim)가
미리 해서 카운트값(정수)만 넘겨준다는 전제로 테스트한다.
"""

from app.billing.notice_rules import validate_notice_rules


def test_추나_연간_20회_이하는_경고없음():
    results = validate_notice_rules(chuna_annual_count=20, chuna_daily_doctor_count=18)
    chuna_warns = [r for r in results if r["rule_id"] == "NOTICE_CHUNA_ANNUAL_LIMIT"]
    assert chuna_warns == []


def test_추나_연간_20회_초과시_경고():
    results = validate_notice_rules(chuna_annual_count=21, chuna_daily_doctor_count=None)
    chuna_warns = [r for r in results if r["rule_id"] == "NOTICE_CHUNA_ANNUAL_LIMIT"]
    assert len(chuna_warns) == 1
    assert chuna_warns[0]["severity"] == "WARN"
    assert "21회" in chuna_warns[0]["message"]


def test_추나_1일_18명_이하는_경고없음():
    results = validate_notice_rules(chuna_annual_count=None, chuna_daily_doctor_count=18)
    daily_warns = [r for r in results if r["rule_id"] == "NOTICE_CHUNA_DAILY_DOCTOR_LIMIT"]
    assert daily_warns == []


def test_추나_1일_18명_초과시_경고():
    results = validate_notice_rules(chuna_annual_count=None, chuna_daily_doctor_count=19)
    daily_warns = [r for r in results if r["rule_id"] == "NOTICE_CHUNA_DAILY_DOCTOR_LIMIT"]
    assert len(daily_warns) == 1
    assert daily_warns[0]["severity"] == "WARN"
    assert "19명" in daily_warns[0]["message"]


def test_둘다_None이면_추나_관련_경고_없음():
    # 이번 청구에 추나 항목이 아예 없는 일반적인 경우 (호출부가 None으로 넘김)
    results = validate_notice_rules(chuna_annual_count=None, chuna_daily_doctor_count=None)
    chuna_rule_ids = {"NOTICE_CHUNA_ANNUAL_LIMIT", "NOTICE_CHUNA_DAILY_DOCTOR_LIMIT"}
    assert not any(r["rule_id"] in chuna_rule_ids for r in results)


def test_추나_경고는_ERROR가_아니라_WARN이라_청구_차단_안함():
    # severity가 WARN이므로 create_claim()의 blocking_errors(ERROR만 필터링)에
    # 걸리지 않아야 한다는 걸 명시적으로 확인
    results = validate_notice_rules(chuna_annual_count=25, chuna_daily_doctor_count=20)
    blocking = [r for r in results if r["severity"] == "ERROR"]
    assert blocking == []
