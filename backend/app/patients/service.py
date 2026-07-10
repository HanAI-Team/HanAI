from datetime import datetime, timezone
from uuid import UUID

from app.core.audit import write_audit
from app.core.models import DataPurgeLog, Doctor, MedicalRecord, Patient
from app.patients.schema import PatientCreate, PatientUpdate
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def create_patient(
    db: AsyncSession, doctor: Doctor, data: PatientCreate
) -> Patient:
    patient = Patient(
        hospital_id=doctor.hospital_id,
        name=data.name,
        birth_date=data.birth_date,
        gender=data.gender,
        phone=data.phone,
        memo=data.memo,
    )
    db.add(patient)
    await db.commit()
    await db.refresh(patient)
    return patient


async def get_patients(
    db: AsyncSession,
    doctor: Doctor,
    page: int,
    size: int,
    search: str | None,
) -> tuple[list[Patient], int]:
    base_query = select(Patient).where(Patient.hospital_id == doctor.hospital_id)

    if search:
        base_query = base_query.where(Patient.name.ilike(f"%{search}%"))

    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar_one()

    patients_result = await db.execute(
        base_query.order_by(Patient.name.asc()).offset((page - 1) * size).limit(size)
    )
    patients = patients_result.scalars().all()

    return list(patients), total


async def get_patient(db: AsyncSession, doctor: Doctor, patient_id: UUID) -> Patient:
    result = await db.execute(
        select(Patient).where(
            Patient.id == patient_id,
            Patient.hospital_id == doctor.hospital_id,
        )
    )
    patient = result.scalar_one_or_none()
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="환자를 찾을 수 없습니다."
        )
    return patient


async def update_patient(
    db: AsyncSession, doctor: Doctor, patient_id: UUID, data: PatientUpdate
) -> Patient:
    patient = await get_patient(db, doctor, patient_id)

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(patient, field, value)

    await db.commit()
    await db.refresh(patient)
    return patient


async def get_patient_with_records(
    db: AsyncSession, doctor: Doctor, patient_id: UUID
) -> tuple[Patient, list[MedicalRecord]]:
    patient = await get_patient(db, doctor, patient_id)

    result = await db.execute(
        select(MedicalRecord)
        .where(
            MedicalRecord.patient_id == patient_id,
            MedicalRecord.recorded_at.isnot(None),
        )
        .order_by(MedicalRecord.recorded_at.desc())
        .limit(5)
    )
    records = list(result.scalars().all())

    return patient, records


async def anonymize_patient  (
    db: AsyncSession,
    doctor: Doctor,
    patient_id: UUID,
)->Patient:
    patient = await get_patient(db, doctor, patient_id)

    name_before = patient.name

    patient.name = "익명"
    patient.phone = None
    patient.rrn = None
    await write_audit(
    db,
    table_name="patients",
    record_id=str(patient_id),
    action="ANONYMIZE",  # 파기 액션
    actor_id=doctor.id,
    actor_type="doctor",
    detail="개인정보 파기: name, phone, rrn 익명화",
)
    db.add(DataPurgeLog(
        hospital_id=doctor.hospital_id,
        doctor_id=doctor.id,
        patient_id=patient_id,
        patient_name_before=name_before,
        reason="환자 요청에 의한 개인정보 파기",
        purge_type="anonymize",
        purged_at=datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
    ))
    await db.commit()
    await db.refresh(patient)
    return patient
    