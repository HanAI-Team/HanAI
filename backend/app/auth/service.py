import re
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schema import RegisterRequest
from app.core.config import settings
from app.core.models import Doctor, Hospital, Subscription


def validate_license_format(license_number: str) -> bool:
    return bool(re.fullmatch(r"\d{8}", license_number))


def create_access_token(doctor_id: UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": str(doctor_id), "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


async def register_doctor(db: AsyncSession, data: RegisterRequest) -> Doctor:
    # 면허번호 중복 체크
    result = await db.execute(
        select(Doctor).where(Doctor.license_number == data.license_number)
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 등록된 면허번호입니다.",
        )

    # Hospital 생성
    hospital = Hospital(
        name=data.clinic_name,
        address=data.clinic_address,
        phone=data.clinic_phone,
    )
    db.add(hospital)
    await db.flush()  # hospital.id 확보

    # Doctor 생성
    doctor = Doctor(
        hospital_id=hospital.id,
        name=data.name,
        license_number=data.license_number,
    )
    db.add(doctor)
    await db.flush()  # doctor.id 확보

    # Subscription 생성
    subscription = Subscription(
        doctor_id=doctor.id,
        tier="basic",
        status="active",
    )
    db.add(subscription)

    await db.commit()
    await db.refresh(doctor)
    return doctor


async def get_doctor_by_license(db: AsyncSession, license_number: str) -> Doctor | None:
    result = await db.execute(
        select(Doctor).where(Doctor.license_number == license_number)
    )
    return result.scalar_one_or_none()
