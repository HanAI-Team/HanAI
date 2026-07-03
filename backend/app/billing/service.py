import calendar
import uuid
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from app.billing.notice_rules import validate_notice_rules

from app.billing.copayment import (
    BillingInput,
    InsuranceType,
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
    Subscription,
)
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Patient.insurance_type 문자열 → InsuranceType 매핑
_INSURANCE_MAP = {
    "health": InsuranceType.HEALTH,
    "medical_aid": InsuranceType.MEDICAL_AID,
    "veterans": InsuranceType.VETERANS,
    "4": InsuranceType.HEALTH,
    "5": InsuranceType.MEDICAL_AID,
    "7": InsuranceType.VETERANS,
}


async def create_claim(
    db: AsyncSession,
    hospital_id: UUID,
    doctor_id: UUID,
    patient_id: UUID,
    medical_record_ids: list[UUID],
    claim_period_year: int,
    claim_period_month: int,
    visit_type: str = "outpatient",
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
        from sqlalchemy import func
        count_result = await db.execute(
            select(func.count(Claim.id)).where(
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
    benefit_total = sum(p.amount or 0 for p in procedures)
    notice_errors = validate_notice_rules(
        patient=patient,
        records=records,
        procedures=procedures,
        claim_period_year=claim_period_year,
        claim_period_month=claim_period_month,
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
    # 본인부담금 계산
    insurance_type = _INSURANCE_MAP.get(patient.insurance_type or "health", InsuranceType.HEALTH)
    billing_result = calculate_billing(BillingInput(
        insurance_type=insurance_type,
        visit_type=VisitType(visit_type),
        benefit_total=benefit_total,
        treatment_days=Decimal(len(records)),
    ))

    # Claim 생성
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
        status="draft",
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
        writer=doctor.name if doctor else "",
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

    for i, record in enumerate(medical_records):
        serial = i + 1
        rec_key = RecordKey(institution_code=inst_code, serial_no=serial, ext_no=0)

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
