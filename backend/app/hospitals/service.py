from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Doctor, Hospital, SaturdayHolidayStaffing
from app.hospitals.schema import HospitalUpdate, StaffingCreate


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
