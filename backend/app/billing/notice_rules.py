from collections import defaultdict
from datetime import date, datetime
from typing import Any


def _get(obj: Any, key: str, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _item_metadata(item: Any) -> dict:
    """procedures 항목의 부가 플래그 딕셔너리.
    MedicalRecordProcedure 등 ORM 객체는 Base.metadata(SQLAlchemy MetaData)를
    상속하고 있어 _get(item, "metadata", {})가 dict가 아닌 값을 돌려줄 수 있다."""
    value = _get(item, "metadata", {})
    return value if isinstance(value, dict) else {}


def _age_at(birth_date: str | date, base_date: str | date) -> int:
    if isinstance(birth_date, str):
        birth_date = datetime.fromisoformat(birth_date).date()
    if isinstance(base_date, str):
        base_date = datetime.fromisoformat(base_date).date()

    age = base_date.year - birth_date.year
    if (base_date.month, base_date.day) < (birth_date.month, birth_date.day):
        age -= 1
    return age


def _item_text(item: Any) -> str:
    return " ".join(
        str(x or "")
        for x in [
            _get(item, "code"),
            _get(item, "name"),
            _get(item, "kor_name"),
            _get(item, "description"),
        ]
    )


def validate_notice_rules(
    patient=None,
    _records=None,
    procedures=None,
    _claim_period_year=None,
    _claim_period_month=None,
    chuna_annual_count: int | None = None,
    chuna_daily_doctor_count: int | None = None,
) -> list[dict[str, Any]]:
    """고시 기반 누락/중복/특정내역 검증.

    chuna_annual_count / chuna_daily_doctor_count는 DB 조회가 필요해 이 함수
    안에서 직접 계산하지 않는다 (이 함수는 순수 함수로 유지). 호출부
    (service.create_claim)가 미리 계산해서 넘겨준다. None이면 해당 검증은
    스킵한다 (예: 이번 청구에 추나 항목이 아예 없는 경우).
    """

    results: list[dict[str, Any]] = []
    items = list(procedures or [])

    # 1) MT038 / JT019 - 보훈국비환자 특정내역
    insurance_type = str(_get(patient, "insurance_type") or "") if patient else ""
    if insurance_type in {"veterans", "7"}:
        results.append({
            "rule_id": "NOTICE_2012_117_MT038",
            "notice_no": "제2012-117호",
            "severity": "ERROR",
            "code": "MT038",
            "message": "보훈국비환자는 MT038 본인부담액 특정내역 기재가 필요합니다.",
        })
        results.append({
            "rule_id": "NOTICE_2012_117_JT019",
            "notice_no": "제2012-117호",
            "severity": "ERROR",
            "code": "JT019",
            "message": "보훈국비환자는 JT019 특정내역 기재가 필요합니다.",
        })

    # 2) 이화학처방 / 촉탁의처방 검증
    for item in items:
        metadata = _item_metadata(item)
        text = _item_text(item)

        is_physicochemical_rx = (
            metadata.get("is_physicochemical_prescription") is True
            or metadata.get("is_entrusted_doctor_prescription") is True
            or "이화학처방" in text
            or "촉탁의처방" in text
        )

        if is_physicochemical_rx and not metadata.get("prescribing_doctor_id"):
            results.append({
                "rule_id": "NOTICE_2008_75_PHYSICOCHEMICAL_RX",
                "notice_no": "제2008-75호",
                "severity": "ERROR",
                "item_code": _get(item, "code"),
                "message": f"{_get(item, 'name', '처방 항목')}은 처방의/촉탁의 정보가 필요합니다.",
            })

    # 3) 동일성분 중복처방 / 중복조정
    ingredient_map: dict[str, list[Any]] = defaultdict(list)
    for item in items:
        ingredient_code = _get(item, "ingredient_code") or _get(item, "ingredientCode")
        if ingredient_code:
            ingredient_map[str(ingredient_code)].append(item)

    for ingredient_code, duplicated_items in ingredient_map.items():
        if len(duplicated_items) < 2:
            continue
        has_reason = any(
            _item_metadata(item).get("duplicate_prescription_reason")
            for item in duplicated_items
        )
        if not has_reason:
            results.append({
                "rule_id": "NOTICE_2008_36_DUPLICATE_INGREDIENT",
                "notice_no": "제2008-36호",
                "severity": "ERROR",
                "ingredient_code": ingredient_code,
                "message": f"동일성분 중복처방이 감지되었습니다. 성분코드 {ingredient_code}의 중복조정 사유가 필요합니다.",
            })

    # 4) 자락침/지각침 특정내역
    for item in items:
        metadata = _item_metadata(item)
        text = _item_text(item)

        is_bloodletting = (
            metadata.get("is_bloodletting_acupuncture") is True
            or "자락침" in text
            or "지각침" in text
            or "刺絡鍼" in text
        )

        if is_bloodletting:
            has_acupoint = (
                metadata.get("acupoint_name")
                or metadata.get("bloodletting_acupoint")
            )
            if not has_acupoint:
                results.append({
                    "rule_id": "NOTICE_2009_18_BLOODLETTING_ACUPUNCTURE",
                    "notice_no": "제2009-18호",
                    "severity": "ERROR",
                    "item_code": _get(item, "code"),
                    "message": f"{_get(item, 'name', '자락침/지각침 항목')}은 혈명 또는 관련 특정내역 기재가 필요합니다.",
                })

    # 5) 공휴일 물리치료 가산 누락 확인
    for item in items:
        metadata = _item_metadata(item)
        category = str(_get(item, "category", "") or "").upper()
        text = _item_text(item)

        is_physiotherapy = category == "전기/온열" or "물리치료" in text
        is_holiday = (
            _get(item, "is_holiday", False)
            or _get(item, "isHoliday", False)
            or metadata.get("is_holiday") is True
        )

        if is_physiotherapy and is_holiday and not metadata.get("holiday_surcharge_applied"):
            results.append({
                "rule_id": "NOTICE_2008_124_HOLIDAY_PHYSIOTHERAPY",
                "notice_no": "제2008-124호",
                "severity": "WARN",
                "item_code": _get(item, "code"),
                "message": f"{_get(item, 'name', '물리치료 항목')}은 공휴일 물리치료 가산 적용 여부 확인이 필요합니다.",
            })

    # 6) 6세 미만 가산 누락 확인
    birth_date = _get(patient, "birth_date") if patient else None
    if birth_date:
        for item in items:
            item_date = (
                _get(item, "date")
                or _get(item, "treatment_date")
                or date.today()
            )
            try:
                age = _age_at(birth_date, item_date)
            except Exception:
                continue

            metadata = _item_metadata(item)
            if age < 6 and not metadata.get("under_six_surcharge_applied"):
                results.append({
                    "rule_id": "NOTICE_2007_127_UNDER_SIX_SURCHARGE",
                    "notice_no": "제2007-127호",
                    "severity": "WARN",
                    "item_code": _get(item, "code"),
                    "message": f"{_get(item, 'name', '진료 항목')}은 6세 미만 가산 적용 여부 확인이 필요합니다.",
                })

    # 7) 장루·요루 치료재료 본인부담률 인하 확인
    patient_disability = str(
        _get(patient, "disability")
        or _get(patient, "disability_type")
        or _get(patient, "disabilityType")
        or ""
    ) if patient else ""

    for item in items:
        metadata = _item_metadata(item)
        category = str(_get(item, "category", "") or "").upper()
        text = _item_text(item)

        is_ostomy_material = (
            category == "MATERIAL"
            and (
                "장루" in text
                or "요루" in text
                or patient_disability.upper() in {"OSTOMY_UROSTOMY", "장루", "요루"}
            )
        )

        if is_ostomy_material and not metadata.get("reduced_copay_applied"):
            results.append({
                "rule_id": "NOTICE_2011_88_OSTOMY_UROSTOMY_MATERIAL",
                "notice_no": "제2011-88호",
                "severity": "WARN",
                "item_code": _get(item, "code"),
                "message": f"{_get(item, 'name', '치료재료')}은 장루·요루 치료재료 본인부담률 인하 적용 여부 확인이 필요합니다.",
            })

    # 8) 추나요법 연간 20회 초과 확인
    # 근거: 국민건강보험법 시행령 별표2 제3호 라목9)·10) — "수진자당 연간 20회"
    # (보건복지부 정책브리핑 2019-03-26 원문, 2025-12 자료까지 동일 확인).
    # ※ "연간" 기산 기준(달력연도 1/1~12/31 vs 최초시술일로부터 365일 롤링)은
    #   원문에 명시된 걸 못 찾아 일단 호출부(create_claim)에서 달력연도로
    #   가정해 카운트한다 — 확정 필요. ERROR가 아니라 WARN인 이유: 실제
    #   초과분에 대한 처리(비급여 전환/청구 자체 불가 등)가 명확히
    #   확인되지 않아, 자동 차단보다는 사람이 확인하게 하는 쪽을 택함.
    if chuna_annual_count is not None and chuna_annual_count > 20:
        results.append({
            "rule_id": "NOTICE_CHUNA_ANNUAL_LIMIT",
            "notice_no": "국민건강보험법 시행령 별표2 제3호 라목9)·10)",
            "severity": "WARN",
            "message": (
                f"이 환자의 올해 누적 추나요법 횟수가 {chuna_annual_count}회로 "
                "연간 급여 인정 한도(20회)를 초과했습니다. 초과분 급여 인정 여부를 확인하세요."
            ),
        })

    # 9) 추나요법 한의사 1인당 1일 18명 초과 확인
    # 근거: 위와 동일 출처 — "한의사 1인은 하루에 18명까지만 진료할 수 있다".
    if chuna_daily_doctor_count is not None and chuna_daily_doctor_count > 18:
        results.append({
            "rule_id": "NOTICE_CHUNA_DAILY_DOCTOR_LIMIT",
            "notice_no": "국민건강보험법 시행령 별표2 제3호 라목9)·10)",
            "severity": "WARN",
            "message": (
                f"담당 한의사의 당일 추나요법 시행 환자 수가 {chuna_daily_doctor_count}명으로 "
                "1일 인정 한도(18명)를 초과했습니다. 초과분 급여 인정 여부를 확인하세요."
            ),
        })

    return results
