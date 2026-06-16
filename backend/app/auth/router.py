from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core.redis import add_token_blacklist
from app.auth.datahub import request_verification, confirm_verification
from app.core.redis import set_verify_pending, get_verify_pending, del_verify_pending


from app.core.deps import get_current_user
from app.core.models import Doctor, StaffAccount
from typing import Union


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
    ResetPasswordResponse,
    StaffLoginRequest,
    VerifyInitResponse,
    VerifyConfirmRequest,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_doctor, _401
from app.core.models import Doctor
from app.subscription.service import get_subscription
from app.core.redis import add_session, remove_session

router = APIRouter(tags=["auth"])
bearer_scheme = HTTPBearer()


import secrets


@router.post("/admin/reset-password/{doctor_id}", response_model=ResetPasswordResponse)
async def reset_password(
    doctor_id: UUID,
    db: AsyncSession = Depends(get_db),
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
):

    if x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="유효하지 않은 관리자 키입니다.")

    result = await db.execute(select(Doctor).where(Doctor.id == doctor_id))

    doctor = result.scalar_one_or_none()
    if doctor is None:
        raise HTTPException(status_code=404, detail="의사를 찾을 수 없습니다.")
    temp_password = secrets.token_urlsafe(8)
    doctor.password_hash = service.pwd_context.hash(temp_password)  # type: ignore
    await db.commit()

    return {"temp_password": temp_password}


# 테스트용
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


# 의사 진짜 인증 하는거 - Step 1: 인증 요청 (네이버/PASS/SMS 등)
@router.post("/register/verify", response_model=VerifyInitResponse, status_code=202)
async def register_verify(data: RegisterVerifyRequest):
    result = await request_verification(
        name=data.name,
        jumin=data.jumin,
        phone=data.phone,
        login_option=data.login_option,
        telecom_gubun=data.telecom_gubun,
    )

    # 즉시 성공(단계 없이 완료)은 드물지만 처리
    if result.get("verified"):
        raise HTTPException(
            status_code=400,
            detail="즉시 인증됨 — /register/verify/confirm 대신 이 응답을 직접 처리하세요.",
        )

    if result.get("error") and not result.get("needs_callback"):
        raise HTTPException(status_code=401, detail=result["error"])

    if not result.get("needs_callback"):
        raise HTTPException(status_code=500, detail="알 수 없는 datahub 응답입니다.")

    callback_id = result["callback_id"]
    set_verify_pending(callback_id, data.model_dump())

    return VerifyInitResponse(
        callback_id=callback_id,
        callback_type=result.get("callback_type", "SIMPLE"),
    )


# Step 2: 앱 인증 완료 후 콜백 결과 조회 + 회원가입
@router.post("/register/verify/confirm", response_model=TokenResponse)
async def register_verify_confirm(
    data: VerifyConfirmRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await confirm_verification(
        callback_id=data.callback_id,
        callback_type=data.callback_type,
        callback_response=data.callback_data,
    )

    if result.get("needs_callback"):
        raise HTTPException(status_code=202, detail="아직 앱 인증이 완료되지 않았습니다.")

    if not result.get("verified"):
        raise HTTPException(
            status_code=401, detail=result.get("error", "면허 인증에 실패했습니다.")
        )

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
    approved = await service.approve_doctor(db, UUID(str(doctor.id)))

    token = service.create_access_token(
        UUID(str(approved["doctor"].id)),
        UUID(str(approved["doctor"].hospital_id)),
        str(approved["doctor"].role),
    )
    return TokenResponse(access_token=token, expires_in=settings.JWT_EXPIRE_MINUTES * 60)


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

    subscription = await get_subscription(db, doctor)
    tier = subscription.tier if subscription else "basic"

    token = service.create_access_token(
        UUID(str(doctor.id)), UUID(str(doctor.hospital_id)), str(doctor.role)
    )
    allowed = await add_session(
        str(doctor.hospital_id), token, str(tier), settings.JWT_EXPIRE_MINUTES * 60
    )
    if not allowed:
        raise HTTPException(
            status_code=429, detail="이미 다른 기기에서 로그인 중입니다."
        )

    return TokenResponse(
        access_token=token,
        expires_in=settings.JWT_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    token = credentials.credentials
    # JWT에서 hospital_id 꺼내기
    from jose import jwt as jose_jwt

    payload = jose_jwt.decode(
        token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )
    hospital_id = payload.get("hospital_id")

    await add_token_blacklist(token, expire_seconds=settings.JWT_EXPIRE_MINUTES * 60)
    if hospital_id:
        await remove_session(hospital_id, token)

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
    doctor.password_hash = service.pwd_context.hash(data.new_password)  # type: ignore
    await db.commit()
    return {"message": "비밀번호가 변경되었습니다."}


@router.get("/admin/pending", response_model=list[PendingDoctorResponse])
async def admin_pending_doctors(
    db: AsyncSession = Depends(get_db),
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
):
    if x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="유효하지 않은 관리자 키입니다.",
        )
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


# @router.get("/me")
# async def get_me(doctor: Doctor = Depends(get_current_doctor)):
#     return {
#         "id": doctor.id,
#         "name": doctor.name,
#         "license_number": doctor.license_number,
#         "role": doctor.role,
#         "hospital_id": doctor.hospital_id,
#     }
@router.get("/me")
async def get_me(
    user: Union[Doctor, StaffAccount] = Depends(get_current_user),
):
    if isinstance(user, Doctor):
        return {
            "id": user.id,
            "name": user.name,
            "license_number": user.license_number,
            "role": user.role,
            "hospital_id": user.hospital_id,
        }
    else:
        return {
            "id": user.id,
            "name": user.name,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "hospital_id": user.hospital_id,
        }

    # JWT role로 Doctor/Staff 구분
    # Doctor면 doctor 정보 반환
    # Staff면 staff 정보 반환


@router.post("/staff/login", response_model=TokenResponse)
async def staff_login(data: StaffLoginRequest, db: AsyncSession = Depends(get_db)):
    staff = await service.get_staff_by_username(db, data.username)
    if staff is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="등록되지 않은 아이디입니다.",
        )
    is_verified = service.pwd_context.verify(data.password, str(staff.password_hash))
    if not is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="비밀번호가 일치하지 않습니다.",
        )
    if not bool(staff.is_active):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다.",
        )
    token = service.create_access_token(
        UUID(str(staff.id)),
        UUID(str(staff.hospital_id)),
        str(staff.role),
    )
    allowed = await add_session(
        str(staff.hospital_id), token, "basic", settings.JWT_EXPIRE_MINUTES * 60
    )
    if not allowed:
        raise HTTPException(
            status_code=429, detail="이미 다른 기기에서 로그인 중입니다."
        )
    return TokenResponse(
        access_token=token,
        expires_in=settings.JWT_EXPIRE_MINUTES * 60,
    )
