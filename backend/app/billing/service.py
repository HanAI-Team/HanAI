import calendar
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from app.billing.catalog import CHUNA_CODES
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
)
from app.core.models import (
    Claim,
    ClaimLineItem,
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
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
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
    needs_review: bool = False
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
        return SpecialCaseResolution(special_code=None, needs_review=False)

    def rate_of(reg: SpecialCaseRegistration) -> Decimal:
        rate, _ = _SPECIAL_CASE_COPAY_RATE.get(reg.special_code, _UNKNOWN_SPECIAL_CODE_RATE)
        return rate

    chosen = min(active, key=rate_of)

    _, needs_review = _SPECIAL_CASE_COPAY_RATE.get(chosen.special_code, _UNKNOWN_SPECIAL_CODE_RATE)
    if _has_f006_concurrent_exception(active):
        needs_review = True
    # V810: 사전승인번호 없으면 공단 미승인 상태 — 담당자 확인 필요
    if chosen.special_code == "V810" and not chosen.prior_approval_number:
        needs_review = True
    if needs_review:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            f"본인부담률 미확인 특정기호 적용: patient_id={patient_id}, special_code={chosen.special_code}"
        )

    return SpecialCaseResolution(
        special_code=chosen.special_code,
        needs_review=needs_review,
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


async def create_claim(
    db: AsyncSession,
    hospital_id: UUID,
    doctor_id: UUID,
    patient_id: UUID,
    medical_record_ids: list[UUID],
    claim_period_year: int,
    claim_period_month: int,
    visit_type: str = "외래",  # "외래" 또는 "입원" (VisitType enum과 일치)
) -> Claim:
    # 환자 조회 및 권한 확인
    r_patient = await db.execute(
        select(Patient).where(Patient.id == patient_id, Patient.hospital_id == hospital_id)
    )
    patient = r_patient.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="환자를 찾을 수 없습니다.")
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
    chuna_total = sum(p.amount or 0 for p in procedures if not p.is_non_benefit and p.fee_master_code in CHUNA_CODES)
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
    ))

    # Claim 생성
    # 추나 연간/1일 한도 WARN이 있으면 needs_review도 함께 세워 화면에 노출한다
    # (ERROR와 달리 청구 생성 자체는 막지 않되, 사람이 재확인하도록).
    needs_review = special_case.needs_review or bool(warn_notices)
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
        special_case_needs_review=needs_review,
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


async def generate_claim_edi(
    db: AsyncSession,
    hospital_id: UUID,
    claim_id: UUID,
    test_mode: bool = False,
) -> bytes:
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
    inst_code = (hospital.institution_code if hospital and hospital.institution_code else "00000000")
    key = RecordKey(institution_code=inst_code, serial_no=1, ext_no=0)

    header = ClaimHeader(
        key=key,
        billing_type="U1",
        treatment_ym=f"{claim.claim_period_year}{claim.claim_period_month:02d}",
        claim_date=datetime.now().strftime("%Y%m%d"),
        claimer=doctor.name if doctor else "",
        writer="상시점검" if test_mode else (doctor.name if doctor else ""),
        writer_rrn="0000000000000",
        claim_count=len(medical_records),
        benefit_total_1=claim.total_amount,
        copayment=claim.patient_copay,
        claim_amount=claim.claim_amount,
    )

    # 3. PatientRecord / DiagnosisRecord / ProcedureDetail 조립
    patient_records = []
    diagnosis_records = []
    procedure_records = []
    special_records = []

    # 의료급여 환자 여부 판정 (MT019 진료확인번호 부착 조건에 사용)
    patient_insurance_type = _INSURANCE_MAP.get(
        (patient.insurance_type if patient else None) or "health", InsuranceType.HEALTH
    )
    is_medical_aid_patient = patient_insurance_type == InsuranceType.MEDICAL_AID

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
        rec_key = RecordKey(institution_code=inst_code, serial_no=serial, ext_no=0)

        is_veterans = patient_insurance_type == InsuranceType.VETERANS
        patient_records.append(PatientRecord(
            key=rec_key,
            employer_code="",
            cert_no="",
            subscriber_name=patient.name if patient else "",
            patient_name=patient.name if patient else "",
            patient_rrn=patient.rrn if patient and patient.rrn else "0000000000000",
            inpatient_days=1,
            benefit_days=1,
            benefit_total_1=claim.total_amount,
            copayment=claim.patient_copay,
            claim_amount=claim.claim_amount,
            benefit_total_2=claim.total_amount + claim.non_benefit_total,
            full_price_copay_total=claim.non_benefit_total,
            under_full_total=claim.total_amount,
            under_full_copay=claim.patient_copay,
            under_full_claim=claim.claim_amount,
            veterans_copay=0,
            under_full_veterans_claim=claim.claim_amount if is_veterans else 0,
            deferred_or_disability=claim.disability_medical_aid,
            support_fund=claim.support_fund,
            # 보완·추가청구(claim_type)일 때만 당초 접수번호/명일련/사유코드를 채워 넣는다.
            receipt_no=claim.original_receipt_no or 0,
            record_serial=claim.original_record_serial or 0,
            reason_code=claim.rejection_reason_code or "  ",
        ))

        # MT032: 접수일시 (명세서 단위, 줄 없음)
        if record.recorded_at:
            special_records.append((serial, SpecialRecord(
                key=rec_key,
                prescription_no=0,
                record_ext_no=0,
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
                prescription_no=0,
                record_ext_no=0,
                special_code="MT019",
                content=patient.confirmation_no,
            )))

        # MT050: 토요일·공휴일 근무현황 (병원 단위 데이터라 청구서 내 첫 명세서에만 1회 부착)
        if i == 0 and mt050_content:
            special_records.append((serial, SpecialRecord(
                key=rec_key,
                prescription_no=0,
                record_ext_no=0,
                special_code="MT050",
                content=mt050_content,
            )))

        # MT008: 의사별 진료일수 (병원 단위 데이터라 청구서 내 첫 명세서에만 1회 부착)
        if i == 0 and mt008_content:
            special_records.append((serial, SpecialRecord(
                key=rec_key,
                prescription_no=0,
                record_ext_no=0,
                special_code="MT008",
                content=mt008_content,
            )))

        # MT002: 산정특례 특정기호 (명세서 단위 — HIRA 별표6 Ⅰ~Ⅳ장 기준)
        # 근거: 청구방법 작성요령 별첨2 ⅱ.1.나.(7) — 의료구분='8', 발생단위구분='1', 특정내역구분='MT002'
        if special_case.special_code and special_case.special_code.startswith("V"):
            special_records.append((serial, SpecialRecord(
                key=rec_key,
                prescription_no=0,
                record_ext_no=0,
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
                    prescription_no=0,
                    record_ext_no=0,
                    special_code="MT014",
                    content=mt014_content,
                )))

            # MT028: 세부상병명 (KCD 코드 없는 희귀질환용. 예: "D12.6/가족성선종성폴립증")
            if special_case.disease_name and special_case.registered_disease_code:
                special_records.append((serial, SpecialRecord(
                    key=rec_key,
                    prescription_no=0,
                    record_ext_no=0,
                    special_code="MT028",
                    content=f"{special_case.registered_disease_code}/{special_case.disease_name}",
                )))

        # DiagnosisRecord
        if record.chart_structured and record.kcd_code:
            diagnosis_records.append((serial, DiagnosisRecord(
                key=rec_key,
                kcd_code=record.kcd_code,
                onset_date=record.recorded_at.strftime("%Y%m%d") if record.recorded_at else "00000000",
                treatment_dept=51,  # 한방 진료과목 코드
                inpatient_route=0,
                prior_dept=0,
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
                    code_gubun="A",
                    code=li.code,
                    unit_price=Decimal(str(li.unit_price or 0)),
                    qty=Decimal(str(li.qty or 1)),
                    days=li.days or 1,
                    amount=li.amount or 0,
                    license_type="3",
                    license_no=doctor.license_number if doctor else "",
                )))
                # JS010: 진료일시 (줄 단위)
                if record.recorded_at:
                    special_records.append((serial, SpecialRecord(
                        key=rec_key,
                        prescription_no=0,
                        record_ext_no=line_no,
                        special_code="JS010",
                        content=record.recorded_at.strftime("%Y%m%d%H%M"),
                    )))
                if li.hyeolmyeong_names:
                    special_records.append((serial, SpecialRecord(
                        key=rec_key,
                        prescription_no=0,
                        record_ext_no=line_no,
                        special_code="JS011",
                        content="/".join(li.hyeolmyeong_names),
                    )))
        else:
            # 구 차팅 경로 폴백: MedicalRecordProcedure 사용
            for proc in [p for p in procedures if p.medical_record_id == record.id]:
                procedure_records.append((serial, ProcedureDetail(
                    key=rec_key,
                    hang=proc.hang or "04",
                    mok=proc.mok or "99",
                    code_gubun=proc.code_gubun or "A",
                    code=proc.fee_master_code or "",
                    unit_price=Decimal(str(proc.unit_price or 0)),
                    qty=Decimal(str(proc.qty or 1)),
                    days=proc.days or 1,
                    amount=proc.amount or 0,
                    license_type=proc.license_type or "3",
                    license_no=doctor.license_number if doctor else "",
                )))
                if proc.special_detail:
                    special_records.append((serial, SpecialRecord(
                        key=rec_key,
                        prescription_no=0,
                        record_ext_no=0,
                        special_code="JS011",
                        content=proc.special_detail,
                    )))

    edi_file = EDIFile(
        header=header,
        patient_records=patient_records,
        diagnosis_records=diagnosis_records,
        procedure_records=procedure_records,
        special_records=special_records,
    )

    return generate_edi(edi_file)
