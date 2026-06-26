import uuid
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.billing.copayment import BillingInput, InsuranceType, VisitType, calculate_billing
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
from collections import defaultdict

from app.core.models import (
    Claim,
    ClaimLineItem,
    Doctor,
    Hospital,
    MedicalRecord,
    MedicalRecordProcedure,
    Patient,
    Prescription,
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

    # 시술 금액 합산
    r_procs = await db.execute(
        select(MedicalRecordProcedure).where(
            MedicalRecordProcedure.medical_record_id.in_([r.id for r in records])
        )
    )
    procedures = r_procs.scalars().all()
    benefit_total = sum(p.amount or 0 for p in procedures)

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