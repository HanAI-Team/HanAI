from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import service
from app.auth.schema import (
    AdminApproveResponse,
    RegisterRequest,
    RegisterResponse,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_doctor
from app.core.models import Doctor

router = APIRouter(tags=["auth"])


@router.post(
    "/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED
)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    if not service.validate_license_format(data.license_number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="면허번호는 8자리 숫자여야 합니다.",
        )

    doctor = await service.register_doctor(db, data)

    return RegisterResponse(
        doctor_id=doctor.id,
        name=str(doctor.name),
        clinic_name=data.clinic_name,
        message="면허 확인 후 최대 24시간 내 승인됩니다.",
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(current_doctor: Doctor = Depends(get_current_doctor)):
    # TODO: Redis 블랙리스트에 토큰 추가
    return {"message": "로그아웃되었습니다."}


@router.post("/admin/approve/{doctor_id}", response_model=AdminApproveResponse)
async def admin_approve(
    doctor_id: UUID,
    db: AsyncSession = Depends(get_db),
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
):
    if x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="유효하지 않은 관리자 키입니다."
        )

    result = await service.approve_doctor(db, doctor_id)
    doctor = result["doctor"]

    return AdminApproveResponse(
        doctor_id=doctor.id,
        name=str(doctor.name),
        access_token=result["access_token"],
        approved_at=doctor.approved_at,
    )
