from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Doctor, DoctorWorkDays, Hospital, SaturdayHolidayStaffing
from app.hospitals.schema import DoctorWorkDaysCreate, HospitalUpdate, StaffingCreate


async def get_hospital(db: AsyncSession, doctor: Doctor, hospital_id: UUID) -> Hospital:
    result = await db.execute(
        select(Hospital).where(
            Hospital.id == hospital_id,
            Hospital.id == doctor.hospital_id,
        )
    )
    hospital = result.scalar_one_or_none()
    if hospital is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="병원을 찾을 수 없습니다."
        )
    return hospital


async def update_hospital(
    db: AsyncSession, doctor: Doctor, hospital_id: UUID, data: HospitalUpdate
) -> Hospital:
    hospital = await get_hospital(db, doctor, hospital_id)

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(hospital, field, value)

    await db.commit()
    await db.refresh(hospital)
    return hospital


async def create_staffing(
    db: AsyncSession, doctor: Doctor, hospital_id: UUID, data: StaffingCreate
) -> SaturdayHolidayStaffing:
    """날짜별 근무 한의사수 등록. 같은 날짜가 이미 있으면 값을 덮어쓴다(upsert)."""
    await get_hospital(db, doctor, hospital_id)  # 소속 병원 검증

    stmt = (
        pg_insert(SaturdayHolidayStaffing)
        .values(hospital_id=hospital_id, work_date=data.work_date, doctor_count=data.doctor_count)
        .on_conflict_do_update(
            index_elements=["hospital_id", "work_date"],
            set_={"doctor_count": data.doctor_count},
        )
        .returning(SaturdayHolidayStaffing)
    )
    result = await db.execute(stmt)
    await db.commit()
    row = result.fetchone()
    return row[0]


async def list_staffing(
    db: AsyncSession, doctor: Doctor, hospital_id: UUID
) -> list[SaturdayHolidayStaffing]:
    await get_hospital(db, doctor, hospital_id)  # 소속 병원 검증

    result = await db.execute(
        select(SaturdayHolidayStaffing)
        .where(SaturdayHolidayStaffing.hospital_id == hospital_id)
        .order_by(SaturdayHolidayStaffing.work_date)
    )
    return list(result.scalars().all())


async def create_doctor_work_days(
    db: AsyncSession, doctor: Doctor, hospital_id: UUID, data: DoctorWorkDaysCreate
) -> DoctorWorkDays:
    """MT008(의사별 진료일수) 산출용 청구월별 의사 근무일수 등록.
    같은 (청구월, 의사)가 이미 있으면 값을 덮어쓴다(upsert)."""
    await get_hospital(db, doctor, hospital_id)  # 소속 병원 검증

    result = await db.execute(
        select(Doctor).where(Doctor.id == data.doctor_id, Doctor.hospital_id == hospital_id)
    )
    target_doctor = result.scalar_one_or_none()
    if target_doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="해당 병원 소속 의사를 찾을 수 없습니다."
        )
    if target_doctor.birth_date is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="생년월일 미등록: PATCH /api/auth/me 로 의사 본인의 생년월일을 먼저 등록해야 합니다.",
        )

    doctor_birth_date = target_doctor.birth_date.strftime("%y%m%d")

    stmt = (
        pg_insert(DoctorWorkDays)
        .values(
            hospital_id=hospital_id,
            doctor_id=data.doctor_id,
            claim_period_year=data.claim_period_year,
            claim_period_month=data.claim_period_month,
            doctor_birth_date=doctor_birth_date,
            work_days=data.work_days,
        )
        .on_conflict_do_update(
            index_elements=["hospital_id", "claim_period_year", "claim_period_month", "doctor_id"],
            set_={"doctor_birth_date": doctor_birth_date, "work_days": data.work_days},
        )
        .returning(DoctorWorkDays)
    )
    result = await db.execute(stmt)
    await db.commit()
    row = result.fetchone()
    return row[0]


async def list_doctor_work_days(
    db: AsyncSession, doctor: Doctor, hospital_id: UUID
) -> list[DoctorWorkDays]:
    await get_hospital(db, doctor, hospital_id)  # 소속 병원 검증

    result = await db.execute(
        select(DoctorWorkDays)
        .where(DoctorWorkDays.hospital_id == hospital_id)
        .order_by(
            DoctorWorkDays.claim_period_year, DoctorWorkDays.claim_period_month, DoctorWorkDays.id
        )
    )
    return list(result.scalars().all())
