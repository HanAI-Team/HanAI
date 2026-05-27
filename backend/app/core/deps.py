from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.models import Doctor, Subscription

bearer_scheme = HTTPBearer(auto_error=False)

_401 = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="인증에 실패했습니다.",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_doctor(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Doctor:
    if credentials is None:
        raise _401

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        doctor_id: str | None = payload.get("sub")
        if doctor_id is None:
            raise _401
    except JWTError:
        raise _401

    result = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = result.scalar_one_or_none()
    if doctor is None:
        raise _401

    return doctor


async def require_standard(
    current_doctor: Doctor = Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
) -> Doctor:
    result = await db.execute(
        select(Subscription).where(Subscription.doctor_id == current_doctor.id)
    )
    subscription = result.scalar_one_or_none()
    if subscription is None or subscription.tier not in ("standard", "premium"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Standard 이상 구독이 필요합니다.",
        )
    return current_doctor


async def require_premium(
    current_doctor: Doctor = Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
) -> Doctor:
    result = await db.execute(
        select(Subscription).where(Subscription.doctor_id == current_doctor.id)
    )
    subscription = result.scalar_one_or_none()
    if subscription is None or str(subscription.tier) != "premium":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium 구독이 필요합니다.",
        )
    return current_doctor
