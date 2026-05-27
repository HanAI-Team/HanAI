from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import service
from app.auth.schema import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
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
        message=f"{doctor.name} 선생님, 회원가입이 완료되었습니다.",
    )


@router.post("/login", response_model=LoginResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    doctor = await service.get_doctor_by_license(db, data.license_number)
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="등록되지 않은 면허번호입니다.",
        )

    # TODO: CODEF 간편인증 요청 연동
    return LoginResponse(
        callback_id="temp_callback_id",
        expires_in=180,
    )


@router.get("/codef/status/{callback_id}", response_model=TokenResponse)
async def codef_status(callback_id: str, db: AsyncSession = Depends(get_db)):
    # TODO: CODEF 인증 상태 실제 조회 (Redis에서 callback_id → doctor_id 매핑 조회)
    if settings.DEBUG:
        result = await db.execute(select(Doctor))
        doctor = result.scalars().first()
        if not doctor:
            raise HTTPException(
                status_code=404,
                detail="테스트용 doctor 없음. 먼저 /register 호출하세요",
            )
        token = service.create_access_token(UUID(str(doctor.id)))
        return TokenResponse(access_token=token, token_type="bearer", expires_in=3600)
    else:
        raise HTTPException(status_code=501, detail="CODEF 연동 준비 중")


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(current_doctor: Doctor = Depends(get_current_doctor)):
    # TODO: Redis 블랙리스트에 토큰 추가
    return {"message": "로그아웃되었습니다."}
