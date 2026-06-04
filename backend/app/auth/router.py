from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core.redis import add_token_blacklist
from app.auth.datahub import verify_medical_license

from app.auth import service
from app.auth.schema import (
    AdminApproveResponse,
    ChangePasswordRequest,
    LoginRequest,
    PendingDoctorResponse,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    RegisterVerifyRequest,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_doctor, _401
from app.core.models import Doctor

router = APIRouter(tags=["auth"])
bearer_scheme = HTTPBearer()


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
        doctor_id=UUID(str(doctor.id)),
        name=str(doctor.name),
        clinic_name=data.clinic_name,
        message="면허 확인 후 최대 24시간 내 승인됩니다.",
    )


@router.post("/register/verify")
async def register_verify(
    data: RegisterVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await verify_medical_license(
        name=data.name,
        jumin=data.jumin,
        phone=data.phone,
        login_option=data.login_option,
    )
    if not result.get("verified"):
        raise HTTPException(status_code=401, detail="면허 인증에 실패했습니다.")

    if result.get("license_number") != data.license_number:
        raise HTTPException(status_code=400, detail="면허번호가 일치하지 않습니다.")

    register_data = RegisterRequest(
        name=data.name,
        license_number=data.license_number,
        password=data.password,
        clinic_name=data.clinic_name,
        clinic_address=data.clinic_address,
        clinic_phone=data.clinic_phone,
    )
    doctor = await service.register_doctor(db, register_data)
    result = await service.approve_doctor(db, UUID(str(doctor.id)))

    token = service.create_access_token(
        UUID(str(result["doctor"].id)),
        UUID(str(result["doctor"].hospital_id)),
        str(result["doctor"].role),
    )
    return TokenResponse(
        access_token=token, expires_in=settings.JWT_EXPIRE_MINUTES * 60
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    doctor = await service.get_doctor_by_license(db, data.license_number)
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="등록되지 않은 면허번호입니다.",
        )
    is_verfied = service.pwd_context.verify(data.password, str(doctor.password_hash))

    if not is_verfied:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="비밀번호가 일치하지 않습니다.",
        )

    if not bool(doctor.is_approved):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="승인 대기 중입니다.",
        )
    return TokenResponse(
        access_token=service.create_access_token(
            UUID(str(doctor.id)), UUID(str(doctor.hospital_id)), str(doctor.role)
        ),
        expires_in=settings.JWT_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    await add_token_blacklist(
        credentials.credentials, expire_seconds=settings.JWT_EXPIRE_MINUTES * 60
    )
    return {"message": "로그아웃되었습니다."}


@router.put("/password", status_code=status.HTTP_200_OK)
async def change_password(
    data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    if not service.pwd_context.verify(data.current_password, str(doctor.password_hash)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="현재 비밀번호가 일치하지 않습니다.",
        )
    doctor.password_hash = service.pwd_context.hash(data.new_password)
    await db.commit()
    return {"message": "비밀번호가 변경되었습니다."}


@router.get("/admin/pending", response_model=list[PendingDoctorResponse])
async def admin_pending_doctors(
    db: AsyncSession = Depends(get_db),
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
):
    if x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="유효하지 않은 관리자 키입니다.")
    return await service.get_pending_doctors(db)


@router.post("/admin/approve/{doctor_id}", response_model=AdminApproveResponse)
async def admin_approve(
    doctor_id: UUID,
    db: AsyncSession = Depends(get_db),
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
):
    if x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="유효하지 않은 관리자 키입니다.",
        )

    result = await service.approve_doctor(db, doctor_id)
    doctor = result["doctor"]

    return AdminApproveResponse(
        doctor_id=doctor.id,
        name=str(doctor.name),
        access_token=result["access_token"],
        approved_at=doctor.approved_at,
    )
