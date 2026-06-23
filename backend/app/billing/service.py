from datetime import datetime
from decimal import Decimal
from uuid import UUID

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
    Doctor,
    MedicalRecord,
    MedicalRecordProcedure,
    Patient,
    Prescription,
)
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


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

    procedures = []
    prescriptions = []
    for record in medical_records:
        r3 = await db.execute(
            select(MedicalRecordProcedure).where(MedicalRecordProcedure.medical_record_id == record.id)
        )
        procedures.extend(r3.scalars().all())
        r4 = await db.execute(
            select(Prescription).where(Prescription.medical_record_id == record.id)
        )
        prescriptions.extend(r4.scalars().all())

    r5 = await db.execute(select(Patient).where(Patient.id == claim.patient_id))
    patient = r5.scalar_one_or_none()

    r6 = await db.execute(select(Doctor).where(Doctor.id == claim.doctor_id))
    doctor = r6.scalar_one_or_none()

    # 2. ClaimHeader 조립
    inst_code = str(claim.hospital_id).replace("-", "")[:8]
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
            patient_rrn="0000000000000",
            inpatient_days=1,
            benefit_days=1,
            benefit_total_1=claim.total_amount,
            copayment=claim.patient_copay,
            claim_amount=claim.claim_amount,
        ))

        # DiagnosisRecord
        if record.chart_structured:
            diagnosis_records.append((serial, DiagnosisRecord(
                key=rec_key,
                kcd_code="U999",  # 실제 KCD 코드 필드 추가 필요
                onset_date=record.recorded_at.strftime("%Y%m%d") if record.recorded_at else "00000000",
                treatment_dept=51,  # 한방 진료과목 코드
                inpatient_route=0,
                prior_dept=0,
                license_kind="3",
                license_no=doctor.license_number if doctor else "",
            )))

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