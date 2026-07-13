import calendar
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from app.billing.catalog import CHUNA_50_CODES, CHUNA_80_CODES, CHUNA_CODES
from app.billing.notice_rules import validate_notice_rules

from app.billing.copayment import (
    BillingInput,
    InsuranceType,
    MedicalAidGrade,
    VisitType,
    calculate_billing,
)
from app.billing.edi_writer import (
    ClaimHeader,
    DiagnosisRecord,
    EDIFile,
    PatientRecord,
    ProcedureDetail,
    RecordKey,
    SpecialRecord,
    generate_edi,
    generate_sam_files,
)
from app.core.models import (
    AcupuncturePoint,
    Claim,
    ClaimLineItem,
    ClaimLineItemAcupoint,
    ClaimResubmissionHistory,
    Doctor,
    DoctorWorkDays,
    Hospital,
    KcdUCode,
    MedicalRecord,
    MedicalRecordProcedure,
    Patient,
    SaturdayHolidayStaffing,
    SpecialCaseRegistration,
    Subscription,
)
from app.billing.schema import ClaimPrescriptionResponse, ClaimStatementResponse, StatementProcedureRow
from app.core.config import settings
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import Optional

# Patient.insurance_type 문자열 → InsuranceType 매핑
_INSURANCE_MAP = {
    "health": InsuranceType.HEALTH,
    "medical_aid": InsuranceType.MEDICAL_AID,
    "veterans": InsuranceType.VETERANS,
    "4": InsuranceType.HEALTH,
    "5": InsuranceType.MEDICAL_AID,
    "7": InsuranceType.VETERANS,
}

# 특정기호별 본인부담률 (산정특례 우선순위 산정용).
# (rate, needs_review) — needs_review=True는 값을 확인 못한 항목.
# rate에는 일반 본인부담률(20%)보다는 낮지만 정확하지 않은 임시값(19%)을
# 넣어, 확정된 값들보다는 항상 후순위로 밀리게 한다.
#
# 2026-07-07 재검증 (law.go.kr 별표4/별표4의2 원문 + HIRA 별표6 종합
# 코드표 직접 대조 완료, copayment.py._special_rate와 동일하게 반영):
#   - V221: 5% → 10%로 정정. "중증화상"이 아니라 별표4(희귀질환자
#     산정특례 대상) 소속 "레쉬-니한증후군(E79.1)" 코드였음. 지난 세션에서
#     "copayment.py(5%) vs 여기(19%, needs_review) 불일치"로 지적됐던 건
#     한 차례 5%로 통일됐었으나, 그 5%라는 값 자체가 틀렸던 것으로 확인됨.
#   - V800: 0% → 10%로 정정. 별표4의2 구분6에 별도 면제 조항 없음, 제5조
#     일반원칙(10%) 적용. V810과 동일 요율이며 차이는 적용기간뿐.
#   - V027: 삭제. "미등록 암환자" 코드였으나 HIRA 고시 제2020-191호
#     (2020-09-01 시행)로 공식 폐지됨. 별표6 Ⅰ~Ⅷ장 전체에도 더 이상
#     존재하지 않음. 개발 단계 DB 조회 결과 기존 등록 데이터 없음
#     (2026-07-07 확인). 혹시 이 코드로 등록된 데이터가 생기면
#     _UNKNOWN_SPECIAL_CODE_RATE(19%, needs_review=True)로 자동
#     처리되어 반드시 사람이 확인하게 된다 — 의도한 동작.
#   - V273(중증외상): law.go.kr 별표3 원문으로 이미 확정(5%)돼 있었으나
#     이 테이블에 실제 반영이 안 돼 있던 것을 뒤늦게 발견해 추가함
#     (copayment.py._special_rate에도 동일하게 누락돼 있어 같이 추가).
_SPECIAL_CASE_COPAY_RATE: dict[str, tuple[Decimal, bool]] = {
    "V193": (Decimal("0.05"), False),  # 암
    "V000": (Decimal("0.00"), False),  # 결핵
    "V010": (Decimal("0.00"), False),  # 잠복결핵
    "V221": (Decimal("0.10"), False),  # 레쉬-니한증후군 (희귀질환, 별표4)
    "V247": (Decimal("0.05"), False),  # 중증화상 (중증도기준1+체표면적기준1)
    "V248": (Decimal("0.05"), False),  # 중증화상 (중증도기준2+체표면적기준2)
    "V250": (Decimal("0.05"), False),  # 중증화상 (별표3 4호 상병)
    "V305": (Decimal("0.05"), False),  # 중증화상 (2021개정 — 외래)
    "V306": (Decimal("0.05"), False),  # 중증화상 (2021개정 — 수술)
    "V800": (Decimal("0.10"), False),  # 중증치매 (별표4의2 구분6 — 일수제한 없음)
    "V810": (Decimal("0.10"), False),  # 중증치매 (별표4의2 구분7 — 연간 60일)
    "V811": (Decimal("0.10"), False),  # 중증치매 (가정간호)
    "V900": (Decimal("0.10"), False),  # 극희귀질환
    "V901": (Decimal("0.10"), False),  # 기타염색체이상질환
    "V999": (Decimal("0.10"), False),  # 상세불명 희귀질환
    "V191": (Decimal("0.05"), False),  # 뇌혈관 (수술O) — 입원 전제, 한의원 적용 희귀
    "V268": (Decimal("0.05"), False),  # 뇌혈관 (중증뇌출혈, 급성기) — 입원 전제
    "V275": (Decimal("0.05"), False),  # 뇌경색 — 입원 전제
    "V192": (Decimal("0.05"), False),  # 심장 — 수술/약제투여 전제
    "V273": (Decimal("0.05"), False),  # 중증외상 (ISS≥15, 권역외상센터 입원) — 입원 전제, 한의원 적용 희귀
    "F006": (Decimal("0.40"), False),  # 신체기능저하군 — 확정 40%.
                                        # 예외: 암환자 등 중증환자 동시해당 시 별도 규정이
                                        # 우선하므로 그 경우는 _has_f006_concurrent_exception()에서
                                        # needs_review=True로 강제 override (이번 스코프에서 별도 규정 미구현)
}
_UNKNOWN_SPECIAL_CODE_RATE = (Decimal("0.19"), True)  # 위 테이블에 없는 특정기호


def _has_f006_concurrent_exception(active: list["SpecialCaseRegistration"]) -> bool:
    """F006(신체기능저하군)이 다른 산정특례와 동시 활성인 경우.

    암환자 등 중증환자가 F006과 동시해당하면 별도 규정이 우선 적용되어야 하는데,
    이번 스코프에서는 그 규정을 구현하지 않았으므로 확정값(40%)을 그대로 믿지 않고
    needs_review=True로 강제해 사람이 다시 확인하게 한다.
    """
    codes = {r.special_code for r in active}
    return "F006" in codes and len(codes) > 1


@dataclass
class SpecialCaseResolution:
    special_code: Optional[str] = None
    review_reason: str | None = None
    registration_number: Optional[str] = None      # MT014용 등록번호 (V810 제외)
    prior_approval_number: Optional[str] = None    # MT014용 사전승인번호 (V810 전용)
    registered_disease_code: Optional[str] = None  # MT028용 유사상병코드
    disease_name: Optional[str] = None             # MT028용 실제상병명


async def resolve_active_special_code(db: AsyncSession, patient_id: UUID) -> SpecialCaseResolution:
    """환자의 활성 산정특례 등록 중 calculate_billing에 넘길 특정기호 하나를 정한다.

    - status="cancelled"는 제외.
    - expires_at이 있고 오늘보다 이전이면 만료로 간주해 제외 (동적 판단, 배치 없음).
    - 여러 건이 동시에 활성 상태면 본인부담률이 가장 낮은 코드를 우선 적용한다
      (산정특례 고시 — 면제/낮은 본인부담률 우선 적용 원칙).
    - 해당하는 등록이 없으면 special_code=None을 반환한다 (기존과 동일하게 일반 본인부담률 적용).
    """
    result = await db.execute(
        select(SpecialCaseRegistration).where(
            SpecialCaseRegistration.patient_id == patient_id,
            SpecialCaseRegistration.status != "cancelled",
        )
    )
    registrations = result.scalars().all()

    today = date.today()
    active = [
        r for r in registrations
        if r.expires_at is None or r.expires_at >= today
    ]
    if not active:
        return SpecialCaseResolution(special_code=None, review_reason=None)

    def rate_of(reg: SpecialCaseRegistration) -> Decimal:
        rate, _ = _SPECIAL_CASE_COPAY_RATE.get(reg.special_code, _UNKNOWN_SPECIAL_CODE_RATE)
        return rate

    chosen = min(active, key=rate_of)

    reasons: list[str] = []
    if chosen.special_code not in _SPECIAL_CASE_COPAY_RATE:
        reasons.append("unconfirmed_rate")
    if _has_f006_concurrent_exception(active):
        reasons.append("f006_concurrent")
    # V810: 사전승인번호 없으면 공단 미승인 상태 — 담당자 확인 필요
    if chosen.special_code == "V810" and not chosen.prior_approval_number:
        reasons.append("v810_no_approval")
    if reasons:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            f"본인부담률 미확인 특정기호 적용: patient_id={patient_id}, special_code={chosen.special_code}"
        )

    return SpecialCaseResolution(
        special_code=chosen.special_code,
        review_reason=",".join(reasons) or None,
        registration_number=chosen.registration_number,
        prior_approval_number=chosen.prior_approval_number,
        registered_disease_code=chosen.registered_disease_code,
        disease_name=chosen.disease_name,
    )


async def _count_annual_chuna_sessions(
    db: AsyncSession, patient_id: UUID, year: int, exclude_medical_record_ids: set[UUID] | None = None
) -> int:
    """환자의 올해(달력연도 1/1~12/31) 누적 추나요법 시행 횟수.

    ※ "연간" 기산 기준이 달력연도인지 최초시술일 기준 365일 롤링인지
      공식 문서에서 확인 못해 달력연도로 가정 — 확정 필요.
    ※ MedicalRecordProcedure(구 차팅 경로)와 ClaimLineItem(BillableItemPicker
      경로) 두 곳에 추나 시술이 나뉘어 저장될 수 있어(dual-path 이슈,
      2026-07-07 발견) 두 테이블을 다 세어 합산한다. 같은 진료기록이
      두 테이블에 동시에 잡히는 경우는 없다고 가정(정상 플로우라면 한
      진료기록당 한 경로만 사용).
    ※ "1회"는 추나 시술이 있었던 서로 다른 MedicalRecord(=방문) 수로 센다
      (하루에 추나 코드가 여러 줄 찍혀도 1회로 취급).
    """
    exclude = exclude_medical_record_ids or set()
    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)

    r1 = await db.execute(
        select(MedicalRecordProcedure.medical_record_id)
        .join(MedicalRecord, MedicalRecord.id == MedicalRecordProcedure.medical_record_id)
        .where(
            MedicalRecord.patient_id == patient_id,
            MedicalRecordProcedure.fee_master_code.in_(CHUNA_CODES),
            MedicalRecord.recorded_at.is_not(None),
            func.date(MedicalRecord.recorded_at) >= year_start,
            func.date(MedicalRecord.recorded_at) <= year_end,
        )
        .distinct()
    )
    ids_from_procedures = {row[0] for row in r1.all()}

    r2 = await db.execute(
        select(ClaimLineItem.medical_record_id)
        .join(MedicalRecord, MedicalRecord.id == ClaimLineItem.medical_record_id)
        .where(
            MedicalRecord.patient_id == patient_id,
            ClaimLineItem.code.in_(CHUNA_CODES),
            MedicalRecord.recorded_at.is_not(None),
            func.date(MedicalRecord.recorded_at) >= year_start,
            func.date(MedicalRecord.recorded_at) <= year_end,
        )
        .distinct()
    )
    ids_from_line_items = {row[0] for row in r2.all()}

    all_record_ids = (ids_from_procedures | ids_from_line_items) - exclude
    return len(all_record_ids)


async def _count_daily_chuna_patients(
    db: AsyncSession, doctor_id: UUID, target_date: date, exclude_patient_id: UUID | None = None
) -> int:
    """특정 한의사가 특정 날짜에 추나요법을 시행한 서로 다른 환자 수.

    ※ 위 _count_annual_chuna_sessions와 동일하게 MedicalRecordProcedure /
      ClaimLineItem 두 경로를 합산한다.
    """
    r1 = await db.execute(
        select(MedicalRecord.patient_id)
        .join(MedicalRecordProcedure, MedicalRecordProcedure.medical_record_id == MedicalRecord.id)
        .where(
            MedicalRecord.doctor_id == doctor_id,
            MedicalRecordProcedure.fee_master_code.in_(CHUNA_CODES),
            MedicalRecord.recorded_at.is_not(None),
            func.date(MedicalRecord.recorded_at) == target_date,
        )
        .distinct()
    )
    patients_from_procedures = {row[0] for row in r1.all()}

    r2 = await db.execute(
        select(MedicalRecord.patient_id)
        .join(ClaimLineItem, ClaimLineItem.medical_record_id == MedicalRecord.id)
        .where(
            MedicalRecord.doctor_id == doctor_id,
            ClaimLineItem.code.in_(CHUNA_CODES),
            MedicalRecord.recorded_at.is_not(None),
            func.date(MedicalRecord.recorded_at) == target_date,
        )
        .distinct()
    )
    patients_from_line_items = {row[0] for row in r2.all()}

    all_patients = patients_from_procedures | patients_from_line_items
    if exclude_patient_id is not None:
        all_patients.discard(exclude_patient_id)
    return len(all_patients)


async def resolve_and_validate_acupoints(
    db: AsyncSession,
    medical_record_id: UUID,
    codes: list[str],
    codes_already_in_request: set[str],
) -> list[AcupuncturePoint]:
    """경혈 코드 목록을 검증하고 AcupuncturePoint 객체 리스트로 반환한다.

    - 존재하지 않는 코드가 있으면 400.
    - 이 진료기록(medical_record_id)에 이미 연결된 경혈 + 이번 요청에서
      먼저 처리된 경혈(codes_already_in_request, 여러 LineItemInput에 걸쳐
      누적 관리는 호출부 책임)을 합쳐 forbidden_with 병용금기 조합을 체크.
    """
    if not codes:
        return []

    unique_codes = list(dict.fromkeys(codes))

    result = await db.execute(
        select(AcupuncturePoint).where(AcupuncturePoint.code.in_(unique_codes))
    )
    found = {p.code: p for p in result.scalars().all()}

    missing = [c for c in unique_codes if c not in found]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"존재하지 않는 경혈 코드입니다: {missing}",
        )

    r_existing = await db.execute(
        select(ClaimLineItemAcupoint.acupuncture_point_code)
        .join(ClaimLineItem, ClaimLineItem.id == ClaimLineItemAcupoint.claim_line_item_id)
        .where(ClaimLineItem.medical_record_id == medical_record_id)
    )
    existing_codes = {row[0] for row in r_existing.all()}
    combined_context = existing_codes | codes_already_in_request

    for code in unique_codes:
        point = found[code]
        if point.forbidden_with:
            others_in_batch = {c for c in unique_codes if c != code}
            conflicts = sorted(
                c for c in point.forbidden_with
                if c in combined_context or c in others_in_batch
            )
            if conflicts:
                raise HTTPException(
                    status_code=400,
                    detail=f"{code}({point.korean_name})는 {conflicts}와 동시 시술 불가합니다.",
                )

    codes_already_in_request.update(unique_codes)
    return [found[c] for c in unique_codes]


async def create_claim(
    db: AsyncSession,
    hospital_id: UUID,
    doctor_id: UUID,
    patient_id: UUID,
    medical_record_ids: list[UUID],
    claim_period_year: int,
    claim_period_month: int,
    visit_type: str = "외래",  # "외래" 또는 "입원" (VisitType enum과 일치)
    approval_no: str | None = None,
) -> Claim:
    # 환자 조회 및 권한 확인
    r_patient = await db.execute(
        select(Patient).where(Patient.id == patient_id, Patient.hospital_id == hospital_id)
    )
    patient = r_patient.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="환자를 찾을 수 없습니다.")

    # 추나요법 사전교육 이수여부 확인용 (notice_rules.py에서 사용, 2026-07-08 추가)
    r_doctor = await db.execute(
        select(Doctor).where(Doctor.id == doctor_id, Doctor.hospital_id == hospital_id)
    )
    doctor_obj = r_doctor.scalar_one_or_none()

    r_sub = await db.execute(select(Subscription).where(Subscription.hospital_id == hospital_id))
    sub = r_sub.scalar_one_or_none()
    tier = sub.tier if sub else "basic"

    if tier == "basic":
        from sqlalchemy import func as _func
        count_result = await db.execute(
            select(_func.count(Claim.id)).where(
                Claim.hospital_id == hospital_id,
                Claim.claim_period_year == claim_period_year,
                Claim.claim_period_month == claim_period_month,
            )
        )
        count = count_result.scalar()
        if count >= 50:
            raise HTTPException(
                status_code=403,
                detail="베이직 플랜은 월 50건까지 청구 가능합니다. 프리미엄으로 업그레이드하세요."
            )

    # 진료기록 조회
    r_records = await db.execute(
        select(MedicalRecord).where(
            MedicalRecord.id.in_(medical_record_ids),
            MedicalRecord.hospital_id == hospital_id,
            MedicalRecord.patient_id == patient_id,
        )
    )
    records = r_records.scalars().all()

    if not records:
        raise HTTPException(status_code=404, detail="진료기록을 찾을 수 없습니다.")

    for record in records:
        if not record.kcd_code:
            raise HTTPException(
                status_code=400,
                detail=f"진료기록({record.id})에 상병코드(KCD)가 입력되지 않았습니다."
            )
        r_kcd = await db.execute(select(KcdUCode).where(KcdUCode.code == record.kcd_code))
        kcd = r_kcd.scalar_one_or_none()

        # ── 남녀 상병 일치 체크 (sex_restriction 있는 코드만) ──────────────────
        if kcd and kcd.sex_restriction:
            gender_map = {"남성": "M", "여성": "F", "남": "M", "여": "F"}
            patient_gender = gender_map.get(patient.gender or "", "")
            if patient_gender and patient_gender != kcd.sex_restriction:
                raise HTTPException(
                    status_code=400,
                    detail=f"상병코드 {record.kcd_code}는 {'여성' if kcd.sex_restriction == 'F' else '남성'} 환자에게만 적용됩니다."
                )

        # ── 법정감염병 경고 (sex_restriction 유무와 무관하게 독립 실행) ──────────
        if kcd and kcd.is_notifiable:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"법정감염병 상병코드 청구: record_id={record.id}, kcd={record.kcd_code}"
            )

    # 시술 금액 합산
    r_procs = await db.execute(
        select(MedicalRecordProcedure).where(
            MedicalRecordProcedure.medical_record_id.in_([r.id for r in records])
        )
    )
    procedures = r_procs.scalars().all()
    benefit_total = sum(p.amount or 0 for p in procedures if not p.is_non_benefit)
    non_benefit_total = sum(p.amount or 0 for p in procedures if p.is_non_benefit)
    # 추나 본인부담률은 코드에 따라 50%/80%로 갈린다 (2026-07-07 확정, catalog.py 참고)
    chuna_total = sum(
        p.amount or 0 for p in procedures
        if not p.is_non_benefit and p.fee_master_code in CHUNA_50_CODES
    )
    chuna_80_total = sum(
        p.amount or 0 for p in procedures
        if not p.is_non_benefit and p.fee_master_code in CHUNA_80_CODES
    )

    # ── 추나요법 연간 20회 / 1일 18명 한도 확인 (이번 청구에 추나 항목이 있을 때만) ──
    chuna_annual_count = None
    chuna_daily_doctor_count = None
    has_chuna = any((p.fee_master_code in CHUNA_CODES) for p in procedures if not p.is_non_benefit)
    if has_chuna:
        this_claim_record_ids = {r.id for r in records}
        prior_annual = await _count_annual_chuna_sessions(
            db, patient_id, claim_period_year, exclude_medical_record_ids=this_claim_record_ids
        )
        # 이번 청구분(진료기록 중 추나 시술이 있는 것)까지 합쳐서 최종 누적치를 만든다.
        this_claim_chuna_records = {
            p.medical_record_id for p in procedures
            if not p.is_non_benefit and p.fee_master_code in CHUNA_CODES
        }
        chuna_annual_count = prior_annual + len(this_claim_chuna_records)

        # 1일 인원 한도는 진료일(레코드의 recorded_at) 기준. 여러 레코드가 섞여 있을 수
        # 있으니 각 진료일마다 확인해야 정확하지만, 여기서는 청구 대표 진료일(가장
        # 빠른 recorded_at)로 단순화한다 — 여러 날짜 진료를 한 청구에 묶는 경우
        # 드물다는 전제. 필요시 레코드별로 세분화 검토.
        recorded_dates = [r.recorded_at.date() for r in records if r.recorded_at]
        if recorded_dates:
            target_date = min(recorded_dates)
            prior_daily = await _count_daily_chuna_patients(
                db, doctor_id, target_date, exclude_patient_id=patient_id
            )
            # 오늘 이 환자 본인도 포함해서 최종 카운트 (본인 1명 + 그 외 환자 수)
            chuna_daily_doctor_count = prior_daily + 1

    # ── 고시 기반 특정내역/청구 검증 (notice_rules.py) ──────────────────────────
    # ※ validate_notice_rules()의 실제 파라미터명은 _records, _claim_period_year,
    #   _claim_period_month (언더스코어 prefix = 함수 내부 미사용 파라미터).
    #   과거 호출부가 records=, claim_period_year=, claim_period_month=로
    #   잘못된 키워드명을 사용해 TypeError가 발생했던 버그를 수정함.
    notice_errors = validate_notice_rules(
        patient=patient,
        _records=records,
        procedures=procedures,
        _claim_period_year=claim_period_year,
        _claim_period_month=claim_period_month,
        chuna_annual_count=chuna_annual_count,
        chuna_daily_doctor_count=chuna_daily_doctor_count,
        doctor=doctor_obj,
    )

    blocking_errors = [e for e in notice_errors if e["severity"] == "ERROR"]

    if blocking_errors:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "고시 기준 필수 특정내역/청구 검증 오류가 있습니다.",
                "errors": blocking_errors,
            },
        )

    warn_notices = [e for e in notice_errors if e["severity"] == "WARN"]

    # 본인부담금 계산
    insurance_type = _INSURANCE_MAP.get(patient.insurance_type or "health", InsuranceType.HEALTH)
    special_case = await resolve_active_special_code(db, patient_id)
    billing_result = calculate_billing(BillingInput(
        insurance_type=insurance_type,
        visit_type=VisitType(visit_type),
        benefit_total=benefit_total,
        non_benefit_total=non_benefit_total,
        treatment_days=Decimal(len(records)),
        special_code=special_case.special_code,
        birth_date=patient.birth_date,
        medical_aid_grade=MedicalAidGrade(patient.medical_aid_grade) if patient.medical_aid_grade else None,
        has_disability=bool(patient.disability_grade),
        chuna_total=chuna_total,
        chuna_80_total=chuna_80_total,
    ))

    # Claim 생성
    existing_reason = special_case.review_reason  # 기존 산정특례 사유 (str|None)
    if bool(warn_notices):
        chuna_reason = "chuna_limit_exceeded"
        review_reason = ",".join(filter(None, [existing_reason, chuna_reason]))
    else:
        review_reason = existing_reason
    claim = Claim(
        id=uuid.uuid4(),
        patient_id=patient_id,
        doctor_id=doctor_id,
        hospital_id=hospital_id,
        claim_period_year=claim_period_year,
        claim_period_month=claim_period_month,
        total_amount=billing_result.benefit_total_1,
        patient_copay=billing_result.copayment,
        claim_amount=billing_result.claim_amount,
        non_benefit_total=non_benefit_total,
        disability_medical_aid=billing_result.disability_medical_cost,
        support_fund=billing_result.support_fund,
        status="draft",
        special_case_review_reason=review_reason,
        approval_no=approval_no,
        warn_notices=warn_notices if warn_notices else None,
    )
    db.add(claim)

    # 진료기록에 claim_id 연결
    for record in records:
        record.claim_id = claim.id

    await db.commit()
    await db.refresh(claim)
    return claim


async def update_claim_resubmission(
    db: AsyncSession,
    hospital_id: UUID,
    actor_id: UUID,
    claim_id: UUID,
    claim_type: str,
    original_receipt_no: int,
    original_record_serial: int,
    rejection_reason_code: str | None,
) -> Claim:
    """보완·추가청구 처리. 반려(rejected)된 청구서에만 적용 가능하며 상태는 바꾸지 않는다."""
    result = await db.execute(select(Claim).where(Claim.id == claim_id, Claim.hospital_id == hospital_id))
    claim = result.scalar_one_or_none()
    if claim is None:
        raise HTTPException(status_code=404, detail="청구서를 찾을 수 없습니다.")
    if claim.status != "rejected":
        raise HTTPException(
            status_code=409, detail="반려된 청구서만 보완·추가청구 처리할 수 있습니다."
        )

    reason_code = rejection_reason_code if claim_type == "supplement" else None

    claim.claim_type = claim_type
    claim.original_receipt_no = original_receipt_no
    claim.original_record_serial = original_record_serial
    claim.rejection_reason_code = reason_code

    db.add(ClaimResubmissionHistory(
        id=uuid.uuid4(),
        claim_id=claim.id,
        actor_id=actor_id,
        claim_type=claim_type,
        receipt_no=original_receipt_no,
        record_serial=original_record_serial,
        reason_code=reason_code,
    ))

    await db.commit()
    await db.refresh(claim)
    return claim


def resolve_institution_code(hospital: Hospital | None, test_mode: bool) -> str:
    """SAM(EDI)과 처방전 등 모든 출력물이 요양기관기호를 같은 소스에서 가져오도록
    통일하는 공용 함수.

    상시점검(테스트) SAM FILE은 실 요양기관기호 대신 심평원에 등록된
    청구소프트웨어 업체기호를 기재하는 것이 공식 방법(신규SW검사
    신청방법.pdf). 테스트 모드가 아닌데 요양기관기호가 비어있으면(과거엔
    "00000000"으로 조용히 채워 MCPoS "청구서·명세서 요양기관기호 불일치"
    오류의 원인이 됐다) 출력 자체를 막고 명확한 에러를 던진다.
    """
    if test_mode:
        return settings.EDI_VENDOR_CODE
    if not hospital or not hospital.institution_code:
        raise HTTPException(
            status_code=400,
            detail="요양기관기호가 설정되지 않아 청구파일을 생성할 수 없습니다. 설정에서 요양기관기호를 입력해주세요.",
        )
    return hospital.institution_code


async def _build_claim_edi_file(
    db: AsyncSession,
    hospital_id: UUID,
    claim_id: UUID,
    test_mode: bool = False,
) -> EDIFile:
    # 1. 데이터 조회
    result = await db.execute(select(Claim).where(Claim.id == claim_id, Claim.hospital_id == hospital_id))
    claim = result.scalar_one_or_none()
    if claim is None:
        raise HTTPException(status_code=404, detail="청구서를 찾을 수 없습니다.")

    r2 = await db.execute(select(MedicalRecord).where(MedicalRecord.claim_id == claim_id))
    medical_records = r2.scalars().all()

    # ClaimLineItem 우선 사용 (BillableItemPicker 경로)
    # 없으면 MedicalRecordProcedure 폴백 (구 차팅 경로)
    r_li = await db.execute(
        select(ClaimLineItem)
        .where(ClaimLineItem.claim_id == claim_id)
        .options(selectinload(ClaimLineItem.acupoints))
        .order_by(ClaimLineItem.created_at)
    )
    all_line_items = r_li.scalars().all()
    line_items_by_record: dict = defaultdict(list)
    for li in all_line_items:
        line_items_by_record[li.medical_record_id].append(li)

    procedures = []
    for record in medical_records:
        if not line_items_by_record.get(record.id):
            r3 = await db.execute(
                select(MedicalRecordProcedure).where(MedicalRecordProcedure.medical_record_id == record.id)
            )
            procedures.extend(r3.scalars().all())

    r5 = await db.execute(select(Patient).where(Patient.id == claim.patient_id))
    patient = r5.scalar_one_or_none()

    r6 = await db.execute(select(Doctor).where(Doctor.id == claim.doctor_id))
    doctor = r6.scalar_one_or_none()

    r7 = await db.execute(select(Hospital).where(Hospital.id == hospital_id))
    hospital = r7.scalar_one_or_none()

    # 2. ClaimHeader 조립
    inst_code = resolve_institution_code(hospital, test_mode)

    treatment_ym = f"{claim.claim_period_year}{claim.claim_period_month:02d}"
    # 청구번호 an(10) = 진료년월(6) + 일련번호(4, 이 앱은 청구서 1건=파일 1개라 항상 "0001").
    claim_no = f"{treatment_ym}0001"

    # 의료급여 환자 여부 판정 (MT019 진료확인번호 부착 조건, 서식번호/보험자종별구분 선택에 사용)
    patient_insurance_type = _INSURANCE_MAP.get(
        (patient.insurance_type if patient else None) or "health", InsuranceType.HEALTH
    )
    is_medical_aid_patient = patient_insurance_type == InsuranceType.MEDICAL_AID
    is_veterans_patient = patient_insurance_type == InsuranceType.VETERANS

    # 보험자종별구분: 건강보험4, 보훈위탁7, 의료급여는 기관 종별(1차/2차)에 따라 1/2 —
    # 이 앱은 한의원(항상 1차 의료기관) 전용이라 의료급여는 "1"로 고정한다.
    insurance_type_code = "1" if is_medical_aid_patient else ("7" if is_veterans_patient else "4")

    # 청구구분(보완/추가/분리): claim.claim_type이 "supplement"/"addition"이면 매핑,
    # "분리청구"는 현재 스키마에 대응 개념이 없어 스코프 아웃 — 필요시 추후 추가.
    # 헤더의 청구구분은 신규일 때 공백이 원문 규격.
    claim_type_code = {"supplement": "1", "addition": "2"}.get(claim.claim_type, "0")
    header_claim_type = " " if claim_type_code == "0" else claim_type_code

    # 서식번호: 헤더는 건강보험/보훈=H010, 의료급여=H011.
    header_form_no = "H011" if is_medical_aid_patient else "H010"
    # 레코드2 서식번호: 이 앱은 Claim에 방문유형(외래/입원)을 저장하는 필드가 없어
    # 항상 외래로 고정 — 입원 케이스 다루게 되면 스키마 추가 필요 (2026-07-09 확인).
    patient_form_no = "K031" if is_medical_aid_patient else "K021"

    header = ClaimHeader(
        claim_no=claim_no,
        form_no=header_form_no,
        institution_code=inst_code,
        insurance_type_code=insurance_type_code,
        claim_type_code=header_claim_type,
        treatment_ym=treatment_ym,
        claim_date=datetime.now().strftime("%Y%m%d"),
        claimer=doctor.name if doctor else "",
        writer="상시점검" if test_mode else (doctor.name if doctor else ""),
        claim_count=len(medical_records),
        benefit_total_1=claim.total_amount,
        copayment=claim.patient_copay,
        claim_amount=claim.claim_amount,
        approval_no=claim.approval_no or "",
        agency_code=(hospital.agency_code if hospital else None) or "",
    )

    if not patient or not patient.rrn:
        raise HTTPException(
            status_code=400,
            detail="환자 주민등록번호가 누락되어 청구파일을 생성할 수 없습니다.",
        )

    # 3. PatientRecord / DiagnosisRecord / ProcedureDetail 조립
    patient_records = []
    diagnosis_records = []
    procedure_records = []
    special_records = []

    # MT050: 토요일·공휴일 근무현황 (병원 단위, 청구서당 1회만 기재 — 첫 명세서에 부착)
    # ※ 내용(content) 바이트 레이아웃은 공식 "명세서 작성요령" 문서를 확보하지 못한 상태의 추정값.
    #   MT008 실사례("YYMMDD/22/YYMMDD/20/...")의 슬래시 구분 표기를 따라
    #   "YYYYMMDD/근무인원수(9(2).V9(1))" 쌍을 날짜순으로 슬래시(/) 연결한다.
    #   예: "20260606/01.0/20260613/00.5" — 공식 스펙 확보 시 재검증 필요.
    last_day = calendar.monthrange(claim.claim_period_year, claim.claim_period_month)[1]
    r_staff = await db.execute(
        select(SaturdayHolidayStaffing)
        .where(
            SaturdayHolidayStaffing.hospital_id == hospital_id,
            SaturdayHolidayStaffing.work_date >= date(claim.claim_period_year, claim.claim_period_month, 1),
            SaturdayHolidayStaffing.work_date <= date(claim.claim_period_year, claim.claim_period_month, last_day),
        )
        .order_by(SaturdayHolidayStaffing.work_date)
    )
    staffing_rows = r_staff.scalars().all()
    mt050_content = "/".join(
        f"{row.work_date.strftime('%Y%m%d')}/{row.doctor_count:04.1f}" for row in staffing_rows
    )

    # MT008: 의사별 진료일수 (병원 단위, 청구서당 1회만 기재 — 첫 명세서에 부착)
    # ※ HIRA 사례집(v089, 외래 사례1)에서 실제 확인된 형식:
    #   "의사생년월일(YYMMDD)/실제진료일수" 쌍을 의사별로 슬래시(/) 연결.
    #   예: "YYMMDD/22/YYMMDD/20/YYMMDD/12"
    #   - 시간제·격일제 의사의 1/2 계산·4사5입·월 15일 상한 적용, "기타" 인력 제외 등은
    #     DoctorWorkDays 테이블 입력 시점에 이미 반영된 최종값이라고 가정한다.
    #     (현재 DoctorWorkDays를 채우는 입력 엔드포인트가 없어 확인 불가 — 추후 재검증 필요)
    #   - 정렬 기준(의사 순서)을 명시한 스펙을 확보 못해 id(입력 순서) 기준으로 정렬한다.
    r_work_days = await db.execute(
        select(DoctorWorkDays)
        .where(
            DoctorWorkDays.hospital_id == hospital_id,
            DoctorWorkDays.claim_period_year == claim.claim_period_year,
            DoctorWorkDays.claim_period_month == claim.claim_period_month,
        )
        .order_by(DoctorWorkDays.id)
    )
    work_days_rows = r_work_days.scalars().all()
    mt008_content = "/".join(
        f"{row.doctor_birth_date}/{row.work_days}" for row in work_days_rows
    )

    special_case = await resolve_active_special_code(db, claim.patient_id)

    for i, record in enumerate(medical_records):
        serial = i + 1
        rec_key = RecordKey(claim_no=claim_no, record_serial=serial)

        # 의료급여종별구분: 1종/2종/노숙인1종 등. 건강보험이면 공란.
        medical_aid_type = " "
        if is_medical_aid_patient and patient and patient.medical_aid_grade:
            medical_aid_type = patient.medical_aid_grade  # "1" 또는 "2" 그대로 사용

        patient_records.append(PatientRecord(
            key=rec_key,
            form_no=patient_form_no,
            institution_code=inst_code,
            employer_code="",
            cert_no="",
            subscriber_name=patient.name if patient else "",
            patient_name=patient.name if patient else "",
            patient_rrn=patient.rrn,
            inpatient_days=1,
            benefit_days=1,
            medical_aid_type=medical_aid_type,
            benefit_total_1=claim.total_amount,
            copayment=claim.patient_copay,
            claim_amount=claim.claim_amount,
            benefit_total_2=claim.total_amount + claim.non_benefit_total,
            full_price_copay_total=claim.non_benefit_total,
            under_full_total=claim.total_amount,
            under_full_copay=claim.patient_copay,
            under_full_claim=claim.claim_amount,
            veterans_copay=0,
            under_full_veterans_claim=claim.claim_amount if is_veterans_patient else 0,
            disability_medical_cost=claim.disability_medical_aid,
            deferred_payment=0,
            support_fund=claim.support_fund,
            # 보완·추가청구(claim_type)일 때만 당초 접수번호/명일련/사유코드를 채워 넣는다.
            receipt_no=claim.original_receipt_no or 0,
            record_serial=claim.original_record_serial or 0,
            reason_code=claim.rejection_reason_code or "  ",
            claim_type_code=claim_type_code,
            first_admission_date="00000000",
        ))

        # MT032: 접수일시 (명세서 단위, 줄 없음)
        if record.recorded_at:
            special_records.append((serial, SpecialRecord(
                key=rec_key,
                record_group_type="1",  # 명세서단위
                line_no=0,
                special_code="MT032",
                content=record.recorded_at.strftime("%Y%m%d%H%M"),
            )))

        # MT019: 진료확인번호 (명세서 단위) — 의료급여 환자이고 confirmation_no가 있을 때만 기재
        # ※ HIRA 사례집(입원 사례 9-1~9-5, 전부 의료급여 1·2종)에서 실제 확인.
        #   현재 confirmation_no를 채우는 API 엔드포인트가 없어(patients 라우터에 미구현),
        #   Patient.confirmation_no 컬럼값을 그대로 사용한다고 가정 — 추후 재검증 필요.
        if is_medical_aid_patient and patient and patient.confirmation_no:
            special_records.append((serial, SpecialRecord(
                key=rec_key,
                record_group_type="1",
                line_no=0,
                special_code="MT019",
                content=patient.confirmation_no,
            )))

        # MT050: 토요일·공휴일 근무현황 (병원 단위 데이터라 청구서 내 첫 명세서에만 1회 부착)
        if i == 0 and mt050_content:
            special_records.append((serial, SpecialRecord(
                key=rec_key,
                record_group_type="1",
                line_no=0,
                special_code="MT050",
                content=mt050_content,
            )))

        # MT008: 의사별 진료일수 (병원 단위 데이터라 청구서 내 첫 명세서에만 1회 부착)
        if i == 0 and mt008_content:
            special_records.append((serial, SpecialRecord(
                key=rec_key,
                record_group_type="1",
                line_no=0,
                special_code="MT008",
                content=mt008_content,
            )))

        # MT002: 산정특례 특정기호 (명세서 단위 — HIRA 별표6 Ⅰ~Ⅳ장 기준)
        # 근거: 청구방법 작성요령 별첨2 ⅱ.1.나.(7) — 의료구분='8', 발생단위구분='1', 특정내역구분='MT002'
        if special_case.special_code and special_case.special_code.startswith("V"):
            special_records.append((serial, SpecialRecord(
                key=rec_key,
                record_group_type="1",
                line_no=0,
                special_code="MT002",
                content=special_case.special_code,
            )))

            # MT014: 산정특례 등록번호 또는 V810 사전승인번호
            # V810(중증치매 일반)은 등록번호 대신 사전승인번호를 기재해야 함
            # (가이드 2-10 — 연간 60일 제한, 공단 사전승인 후 번호 발급)
            if special_case.special_code == "V810":
                mt014_content = special_case.prior_approval_number
            else:
                mt014_content = special_case.registration_number
            if mt014_content:
                special_records.append((serial, SpecialRecord(
                    key=rec_key,
                    record_group_type="1",
                    line_no=0,
                    special_code="MT014",
                    content=mt014_content,
                )))

            # MT028: 세부상병명 (KCD 코드 없는 희귀질환용. 예: "D12.6/가족성선종성폴립증")
            if special_case.disease_name and special_case.registered_disease_code:
                special_records.append((serial, SpecialRecord(
                    key=rec_key,
                    record_group_type="1",
                    line_no=0,
                    special_code="MT028",
                    content=f"{special_case.registered_disease_code}/{special_case.disease_name}",
                )))

        # DiagnosisRecord — 레코드 2-1(상병내역)은 명세서(레코드2)마다 최소 1건 필수(HIRA 규격).
        if not record.kcd_code:
            raise HTTPException(
                status_code=400,
                detail=f"진료기록({record.id})에 상병코드(KCD)가 입력되지 않아 청구파일을 생성할 수 없습니다.",
            )
        r_kcd = await db.execute(select(KcdUCode).where(KcdUCode.code == record.kcd_code))
        kcd = r_kcd.scalar_one_or_none()
        today = date.today()
        if not kcd or (kcd.effective_date and kcd.effective_date > today) or (kcd.expired_date and kcd.expired_date < today):
            raise HTTPException(
                status_code=400,
                detail=f"진료기록({record.id})의 상병코드 '{record.kcd_code}'는 청구 가능한 KCD 완전코드가 아닙니다.",
            )
        diagnosis_records.append((serial, DiagnosisRecord(
            key=rec_key,
            kcd_code=record.kcd_code,
            onset_date=record.recorded_at.strftime("%Y%m%d") if record.recorded_at else "00000000",
            treatment_dept=9,  # 진료과목: 09=한의과
            license_kind="3",
            license_no=doctor.license_number if doctor else "",
        )))

        record_line_items = line_items_by_record.get(record.id, [])
        if record_line_items:
            # BillableItemPicker 경로: ClaimLineItem 사용
            for line_no, li in enumerate(record_line_items, start=1):
                procedure_records.append((serial, ProcedureDetail(
                    key=rec_key,
                    hang=li.hang,
                    mok=li.mok,
                    line_no=line_no,
                    code_gubun="A",
                    code=li.code,
                    unit_price=Decimal(str(li.unit_price or 0)),
                    qty=Decimal(str(li.qty or 1)),
                    days=li.days or 1,
                    amount=li.amount or 0,
                    license_kind="3",
                    license_no=doctor.license_number if doctor else "",
                )))
                # JS010: 진료일시 (줄 단위 — 발생단위구분='2' 줄번호단위)
                if record.recorded_at:
                    special_records.append((serial, SpecialRecord(
                        key=rec_key,
                        record_group_type="2",
                        line_no=line_no,
                        special_code="JS010",
                        content=record.recorded_at.strftime("%Y%m%d%H%M"),
                    )))
                if li.acupoints:
                    ordered_codes = [a.acupuncture_point_code for a in li.acupoints]
                    special_records.append((serial, SpecialRecord(
                        key=rec_key,
                        record_group_type="2",
                        line_no=line_no,
                        special_code="JS011",
                        content="/".join(ordered_codes),
                    )))
        else:
            # 구 차팅 경로 폴백: MedicalRecordProcedure 사용
            for line_no, proc in enumerate(
                [p for p in procedures if p.medical_record_id == record.id], start=1
            ):
                procedure_records.append((serial, ProcedureDetail(
                    key=rec_key,
                    hang=proc.hang or "04",
                    mok=proc.mok or "99",
                    line_no=line_no,
                    code_gubun=proc.code_gubun or "A",
                    code=proc.fee_master_code or "",
                    unit_price=Decimal(str(proc.unit_price or 0)),
                    qty=Decimal(str(proc.qty or 1)),
                    days=proc.days or 1,
                    amount=proc.amount or 0,
                    license_kind="3",
                    license_no=doctor.license_number if doctor else "",
                )))
                if proc.special_detail:
                    special_records.append((serial, SpecialRecord(
                        key=rec_key,
                        record_group_type="1",  # 줄 번호를 특정 못해 명세서단위로 기재 (구 경로 한계)
                        line_no=0,
                        special_code="JS011",
                        content=proc.special_detail,
                    )))

    # 청구서(H010) 헤더의 합계 필드는 모든 명세서(K020.1)의 대응 필드를 합산한
    # 값이어야 한다 — 기존엔 0으로 고정 출력되어 MCPoS "청구서, 명세서 불일치"
    # 오류가 발생했다 (2026-07-13 실측 확인).
    header.benefit_total_2 = sum(p.benefit_total_2 for p in patient_records)
    header.under_full_total = sum(p.under_full_total for p in patient_records)
    header.under_full_copay = sum(p.under_full_copay for p in patient_records)
    header.under_full_claim = sum(p.under_full_claim for p in patient_records)

    return EDIFile(
        header=header,
        patient_records=patient_records,
        diagnosis_records=diagnosis_records,
        procedure_records=procedure_records,
        special_records=special_records,
    )


async def generate_claim_edi(
    db: AsyncSession,
    hospital_id: UUID,
    claim_id: UUID,
    test_mode: bool = False,
) -> bytes:
    edi_file = await _build_claim_edi_file(db, hospital_id, claim_id, test_mode)
    return generate_edi(edi_file)


async def generate_claim_sam_files(
    db: AsyncSession,
    hospital_id: UUID,
    claim_id: UUID,
    test_mode: bool = False,
) -> dict[str, bytes]:
    """SAM File 생성 디렉토리(/HIRA/DDMD/SAM/IN/)에 들어갈 개별 파일들.

    한방 명세서는 H010(청구서, 공통) + K020.1(일반내역)~K020.4(특정내역)
    4개 파일로 나뉜다 (의·치과처럼 청구서+명세서가 한 파일로 합쳐지지
    않음). 압축·암호화는 별도의 전자청구 프로그램이 담당하므로 여기서는
    원본 파일 생성까지만 다룬다.

    ※ K020.1~4가 정확히 어떤 레코드에 대응하는지는 SAM File Layout
    원문으로 확정한 게 아니라 "일반내역/상병내역/진료내역/특정내역"
    순서 정황상 추정한 매핑이다 (2026-07-10). 확정 자료 확보 시 재검증 필요.
    """
    edi_file = await _build_claim_edi_file(db, hospital_id, claim_id, test_mode)
    return generate_sam_files(edi_file)


async def build_claim_statement(
    db: AsyncSession, hospital_id: UUID, claim_id: UUID
) -> ClaimStatementResponse:
    """요양급여비용명세서(한방외래, 별지18호/GI013) 출력용 데이터 조립.

    본인일부부담금(copayment)·청구액(claim_amount)은 실제 EDI 제출에 쓰인
    claim.patient_copay/claim_amount를 그대로 사용한다 (재계산 값이 아님 —
    support_fund 변경(PATCH /support-fund) 등으로 생성 시점과 달라졌더라도
    실제 청구된 금액과 명세서가 항상 일치하도록). 그 외 보험자종별에 따른
    세부 항목(건강보험/의료급여/보훈 등 버킷 분류)은 claim.total_amount/
    non_benefit_total로 calculate_billing()을 다시 호출해 판별한다.
    """
    result = await db.execute(
        select(Claim).where(Claim.id == claim_id, Claim.hospital_id == hospital_id)
    )
    claim = result.scalar_one_or_none()
    if claim is None:
        raise HTTPException(status_code=404, detail="청구서를 찾을 수 없습니다.")

    r2 = await db.execute(select(MedicalRecord).where(MedicalRecord.claim_id == claim_id))
    medical_records = r2.scalars().all()

    r_li = await db.execute(
        select(ClaimLineItem)
        .where(ClaimLineItem.claim_id == claim_id)
        .order_by(ClaimLineItem.created_at)
    )
    all_line_items = r_li.scalars().all()
    line_items_by_record: dict = defaultdict(list)
    for li in all_line_items:
        line_items_by_record[li.medical_record_id].append(li)

    procedures = []
    for record in medical_records:
        if not line_items_by_record.get(record.id):
            r3 = await db.execute(
                select(MedicalRecordProcedure).where(MedicalRecordProcedure.medical_record_id == record.id)
            )
            procedures.extend(r3.scalars().all())

    patient = await db.get(Patient, claim.patient_id)
    doctor = await db.get(Doctor, claim.doctor_id)
    hospital = await db.get(Hospital, hospital_id)

    # 상병명 (진료기록에 연결된 KCD 코드 전체, 중복 제거)
    kcd_codes = sorted({r.kcd_code for r in medical_records if r.kcd_code})
    disease_names = []
    for code in kcd_codes:
        r_kcd = await db.execute(select(KcdUCode).where(KcdUCode.code == code))
        kcd = r_kcd.scalar_one_or_none()
        disease_names.append(f"{code} {kcd.korean_name}" if kcd else code)

    # 내원일자
    visit_dates = sorted({
        (r.recorded_at or r.created_at).date()
        for r in medical_records if r.recorded_at or r.created_at
    })

    # 진료내역 (hang, mok, code) 단위 합산 — ClaimLineItem 우선, 없으면 MedicalRecordProcedure 폴백
    grouped: dict = {}

    def _add_row(hang, mok, code, name, unit_price, amount, is_non_benefit):
        key = (hang, mok, code)
        if key not in grouped:
            copay_label = "A" if code in CHUNA_50_CODES else ("B" if code in CHUNA_80_CODES else None)
            grouped[key] = {
                "hang": hang or "04", "mok": mok or "99", "code": code or "",
                "name": name or "", "unit_price": int(unit_price or 0),
                "count": 0, "amount": 0, "is_non_benefit": is_non_benefit,
                "copay_rate_label": copay_label,
            }
        grouped[key]["count"] += 1
        grouped[key]["amount"] += int(amount or 0)

    for li in all_line_items:
        _add_row(li.hang, li.mok, li.code, li.name, li.unit_price, li.amount, li.is_non_benefit)
    for proc in procedures:
        _add_row(
            proc.hang, proc.mok, proc.fee_master_code,
            proc.fee_master.name if proc.fee_master else proc.procedure_type,
            proc.unit_price, proc.amount, proc.is_non_benefit,
        )

    procedure_rows = [StatementProcedureRow(**v) for v in grouped.values()]

    special_case = await resolve_active_special_code(db, claim.patient_id)

    chuna_total = sum(v["amount"] for v in grouped.values() if v["copay_rate_label"] == "A")
    chuna_80_total = sum(v["amount"] for v in grouped.values() if v["copay_rate_label"] == "B")

    ins = _INSURANCE_MAP.get((patient.insurance_type if patient else None) or "health", InsuranceType.HEALTH)
    aid_grade = None
    if patient and patient.medical_aid_grade == "1":
        aid_grade = MedicalAidGrade.GRADE_1
    elif patient and patient.medical_aid_grade == "2":
        aid_grade = MedicalAidGrade.GRADE_2

    billing_result = calculate_billing(BillingInput(
        insurance_type=ins,
        # Claim에 방문유형(외래/입원)을 저장하는 필드가 없어 항상 외래로 고정
        # (EDI writer와 동일한 기존 제약, 위 generate_claim_edi 주석 참고).
        visit_type=VisitType.OUTPATIENT,
        benefit_total=claim.total_amount - claim.non_benefit_total,
        non_benefit_total=claim.non_benefit_total,
        medical_aid_grade=aid_grade,
        has_disability=bool(patient.disability_grade) if patient else False,
        birth_date=patient.birth_date if patient else None,
        special_code=special_case.special_code,
        support_fund=claim.support_fund,
        chuna_total=chuna_total,
        chuna_80_total=chuna_80_total,
    ))

    birth_masked = (
        f"{patient.birth_date.strftime('%y%m%d')}-XXXXXXX" if patient and patient.birth_date else "-"
    )

    return ClaimStatementResponse(
        hospital_name=hospital.name if hospital else "-",
        institution_code=hospital.institution_code if hospital and hospital.institution_code else "-",
        patient_name=patient.name if patient else "-",
        birth_masked=birth_masked,
        disease_names=disease_names,
        special_code=special_case.special_code,
        doctor_name=doctor.name if doctor else "-",
        license_type="한의사",
        license_no=doctor.license_number if doctor else "-",
        visit_dates=[d.strftime("%Y-%m-%d") for d in visit_dates],
        visit_count=len(visit_dates),
        procedures=procedure_rows,
        subtotal=billing_result.benefit_total_1,
        surcharge_rate=0.0,
        benefit_total_1=billing_result.benefit_total_1,
        copayment=claim.patient_copay,
        support_fund=claim.support_fund,
        disability_medical_cost=claim.disability_medical_aid,
        claim_amount=claim.claim_amount,
        upper_limit_excess=billing_result.upper_limit_excess,
        non_benefit_total=claim.non_benefit_total,
        benefit_total_2=billing_result.benefit_total_2,
        veterans_claim=billing_result.veterans_claim,
        full_price_copay_total=billing_result.full_price_copay_total,
        veterans_copay=billing_result.veterans_copay,
        under_full_total=billing_result.under_full_total,
        under_full_copay=billing_result.under_full_copay,
        under_full_claim=billing_result.under_full_claim,
        under_full_veterans_claim=billing_result.under_full_veterans_claim,
    )


async def build_claim_prescription(
    db: AsyncSession, hospital_id: UUID, claim_id: UUID, test_mode: bool = False
) -> ClaimPrescriptionResponse:
    """처방전(별지9호서식) 출력용 데이터 조립.

    약품 항목 입력 기능이 없어 상단부(기관·환자·처방의료인 정보)만 채운다
    — build_claim_statement()의 상병명/생년월일마스킹 계산과 동일한 방식.
    요양기관기호는 SAM(EDI) 생성과 동일한 resolve_institution_code()를 써서
    두 출력물이 서로 다른 값을 보여주는 일이 없도록 한다.
    """
    result = await db.execute(
        select(Claim).where(Claim.id == claim_id, Claim.hospital_id == hospital_id)
    )
    claim = result.scalar_one_or_none()
    if claim is None:
        raise HTTPException(status_code=404, detail="청구서를 찾을 수 없습니다.")

    r2 = await db.execute(select(MedicalRecord).where(MedicalRecord.claim_id == claim_id))
    medical_records = r2.scalars().all()

    patient = await db.get(Patient, claim.patient_id)
    doctor = await db.get(Doctor, claim.doctor_id)
    hospital = await db.get(Hospital, hospital_id)
    institution_code = resolve_institution_code(hospital, test_mode)

    kcd_codes = sorted({r.kcd_code for r in medical_records if r.kcd_code})
    disease_names = []
    for code in kcd_codes:
        r_kcd = await db.execute(select(KcdUCode).where(KcdUCode.code == code))
        kcd = r_kcd.scalar_one_or_none()
        disease_names.append(f"{code} {kcd.korean_name}" if kcd else code)

    visit_dates = sorted({
        (r.recorded_at or r.created_at).date()
        for r in medical_records if r.recorded_at or r.created_at
    })
    issue_date = (visit_dates[-1] if visit_dates else date.today()).strftime("%Y-%m-%d")

    birth_masked = (
        f"{patient.birth_date.strftime('%y%m%d')}-XXXXXXX" if patient and patient.birth_date else "-"
    )

    return ClaimPrescriptionResponse(
        hospital_name=hospital.name if hospital else "-",
        institution_code=institution_code,
        hospital_phone=hospital.phone if hospital and hospital.phone else "-",
        issue_date=issue_date,
        issue_no=f"{claim.claim_period_year}{claim.claim_period_month:02d}0001",
        patient_name=patient.name if patient else "-",
        patient_birth_masked=birth_masked,
        disease_names=disease_names,
        doctor_name=doctor.name if doctor else "-",
        license_type="한의사",
        license_no=doctor.license_number if doctor else "-",
    )
