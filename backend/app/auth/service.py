import re
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from app.auth.schema import RegisterRequest
from app.core.config import settings
from app.core.models import (
    AccountHistory,
    Doctor,
    Hospital,
    PasswordHistory,
    Subscription,
)
from fastapi import HTTPException, status
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# pwd_context.verify(plain_password, hashed_password)


def validate_license_format(license_number: str) -> bool:
    return bool(re.fullmatch(r"\d{4,}", license_number))

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


async def register_doctor(
    db: AsyncSession, data: RegisterRequest, birth_date: date | None = None
) -> Doctor:
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
        birth_date=birth_date,
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


async def deactivate_doctor(db: AsyncSession, doctor_id: UUID) -> Doctor:
    result = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = result.scalar_one_or_none()
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="의사를 찾을 수 없습니다."
        )

    doctor.is_active = False  # type: ignore
    await db.commit()
    await db.refresh(doctor)
    return doctor


async def get_staff_by_username(db: AsyncSession, username: str):
    from app.core.models import StaffAccount

    result = await db.execute(
        select(StaffAccount).where(StaffAccount.username == username)
    )
    return result.scalar_one_or_none()



def validate_password_complexity(password :str)->list[str]:
    errors = []

    if len(password) < 8:
        errors.append("비밀번호는 8자 이상이어야 합니다.")

    if not re.search(r"[A-Za-z]", password):
        errors.append("영문자를 포함해야 합니다.")
    
    if not re.search(r"\d", password):
        errors.append("숫자를 포함해야 합니다.")

    if not re.search(r"[!@#$%^&*()_+\-=\[\]{}|;:',.<>?/~`]", password):
        errors.append("특수문자를 포함해야 합니다.")

    return errors 



async def check_password_history(
        db: AsyncSession,
        account_type:str,
        account_id : UUID,
        new_password: str,
        limit :int =5
)->bool:
    result = await db.execute(select(PasswordHistory).where(
        PasswordHistory.account_type == account_type,
        PasswordHistory.account_id == account_id
    ).limit(limit=limit))
    password_history = result.scalars().all()

    return any(pwd_context.verify(new_password, h.password_hash) for h in password_history)


async def save_password_history(
    db: AsyncSession,
    account_type: str,
    account_id: UUID,
    password_hash: str,
) -> None:
    password_history = PasswordHistory(
        account_type  = account_type,
        account_id = account_id,
        password_hash = password_hash
    )
    db.add(password_history)
  




async def record_account_history(
        db:AsyncSession,
        account_type : str,
        account_id :UUID,
        action:str,
        actor_id : UUID | None = None,
        detail:str | None = None
)->None:
    account_history = AccountHistory(
        account_type = account_type,
        account_id  = account_id,
        action = action ,
        actor_id = actor_id,
        detail=detail
    )
    db.add(account_history)

    