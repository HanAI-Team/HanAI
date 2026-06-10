import re
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext

from app.auth.schema import RegisterRequest
from app.core.config import settings
from app.core.models import Doctor, Hospital, Subscription

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# pwd_context.verify(plain_password, hashed_password)


def validate_license_format(license_number: str) -> bool:
    return bool(re.fullmatch(r"\d{8}", license_number))


def create_access_token(doctor_id: UUID, hospital_id: UUID, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {
        "sub": str(doctor_id),
        "hospital_id": str(hospital_id),
        "role": role,
        "exp": expire,
    }
    return jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


async def register_doctor(db: AsyncSession, data: RegisterRequest) -> Doctor:
    result = await db.execute(
        select(Doctor).where(Doctor.license_number == data.license_number)
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 등록된 면허번호입니다.",
        )

    hospital = Hospital(
        name=data.clinic_name,
        address=data.clinic_address,
        phone=data.clinic_phone,
    )
    db.add(hospital)
    await db.flush()

    doctor = Doctor(
        hospital_id=hospital.id,
        name=data.name,
        license_number=data.license_number,
        password_hash=pwd_context.hash(data.password),
        role="owner",
    )
    db.add(doctor)
    await db.flush()

    subscription = Subscription(
        hospital_id=hospital.id,
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


async def get_pending_doctors(db: AsyncSession) -> list:
    from app.core.models import Hospital
    from sqlalchemy import join

    result = await db.execute(
        select(Doctor, Hospital.name.label("clinic_name"))
        .join(Hospital, Doctor.hospital_id == Hospital.id)
        .where(Doctor.is_approved == False)  # noqa: E712
        .order_by(Doctor.created_at)
    )
    rows = result.all()
    return [
        {
            "doctor_id": row.Doctor.id,
            "name": row.Doctor.name,
            "license_number": row.Doctor.license_number,
            "clinic_name": row.clinic_name,
            "created_at": row.Doctor.created_at,
        }
        for row in rows
    ]


async def approve_doctor(db: AsyncSession, doctor_id: UUID) -> dict:
    result = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = result.scalar_one_or_none()
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="의사를 찾을 수 없습니다."
        )
    if bool(doctor.is_approved):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="이미 승인된 의사입니다."
        )

    doctor.is_approved = True  # type: ignore
    doctor.approved_at = datetime.now(timezone.utc)  # type: ignore
    await db.commit()
    await db.refresh(doctor)

    access_token = create_access_token(
        UUID(str(doctor.id)), UUID(str(doctor.hospital_id)), str(doctor.role)
    )
    return {"doctor": doctor, "access_token": access_token}


async def get_staff_by_email(db: AsyncSession, email: str):
    from app.core.models import StaffAccount

    result = await db.execute(select(StaffAccount).where(StaffAccount.email == email))
    return result.scalar_one_or_none()
