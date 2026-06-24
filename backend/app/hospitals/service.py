from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Doctor, Hospital
from app.hospitals.schema import HospitalUpdate


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
