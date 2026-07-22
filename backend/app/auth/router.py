import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Union
from uuid import UUID

from app.auth import service
from app.auth.datahub import (
    confirm_verification,
    extract_birth_date,
    request_verification,
)
from app.auth.schema import (
    AdminApproveResponse,
    ChangePasswordRequest,
    DoctorProfileUpdate,
    LoginRequest,
    PendingDoctorResponse,
    RegisterRequest,
    RegisterResponse,
    RegisterVerifyRequest,
    ResetPasswordResponse,
    StaffLoginRequest,
    TokenResponse,
    VerifyConfirmRequest,
    VerifyInitResponse,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_doctor, get_current_user
from app.core.models import (
    AccessControlLog,
    AccountHistory,
    AuditLog,
    Doctor,
    Hospital,
    LoginLog,
    StaffAccount,
    Subscription,
)
from app.core.redis import (
    VerifyPendingDecryptionError,
    add_session,
    add_token_blacklist,
    del_verify_pending,
    get_redis,
    get_verify_pending,
    remove_session,
    set_verify_pending,
)
from app.subscription.service import get_subscription
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])
bearer_scheme = HTTPBearer()


_redis = get_redis()

MAX_FAIL = 5
LOCK_SECONDS = 60 * 30  # 30분


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
    doctor.password_hash = service.pwd_context.hash(temp_password)
    doctor.force_password_change = True  
    await db.commit()
    return {"temp_password": temp_password}


@router.post("/admin/reset-password/staff/{staff_id}", response_model=ResetPasswordResponse)
async def reset_staff_password(
    staff_id: UUID,
    db: AsyncSession = Depends(get_db),
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
):
    if x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="유효하지 않은 관리자 키입니다.")

    result = await db.execute(select(StaffAccount).where(StaffAccount.id == staff_id))
    staff = result.scalar_one_or_none()
    if staff is None:
        raise HTTPException(status_code=404, detail="직원을 찾을 수 없습니다.")
    temp_password = secrets.token_urlsafe(8)
    staff.password_hash = service.pwd_context.hash(temp_password)
    staff.force_password_change = True
    await db.commit()
    return {"temp_password": temp_password}


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    if not service.validate_license_format(data.license_number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="면허번호는 4자리 이상 숫자여야 합니다.",
        )
    doctor = await service.register_doctor(db, data)
    await service.record_account_history(db, "doctor", doctor.id , "created")
    return RegisterResponse(
        doctor_id=UUID(str(doctor.id)),
        name=str(doctor.name),
        clinic_name=data.clinic_name,
        message="면허 확인 후 최대 24시간 내 승인됩니다.",
    )


@router.post("/register/verify", response_model=VerifyInitResponse, status_code=202)
async def register_verify(data: RegisterVerifyRequest):
    result = await request_verification(
        name=data.name,
        jumin=data.jumin,
        phone=data.phone,
        login_option=data.login_option,
        telecom_gubun=data.telecom_gubun,
    )
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

    # /register/verify에서 저장해둔 jumin(주민번호)에서 생년월일을 뽑아낸다.
    # pending 조회 실패나 형식 불일치는 회원가입을 막지 않고 birth_date만 비워두되,
    # 실패 사유와 callback_id는 로그로 남긴다 (jumin 원본은 절대 로그에 남기지 않는다).
    try:
        pending = get_verify_pending(data.callback_id)
    except VerifyPendingDecryptionError:
        logger.warning(
            "[register_verify_confirm] pending 데이터 복호화 실패 (callback_id=%s)",
            data.callback_id,
        )
        pending = None

    if pending is None:
        logger.info(
            "[register_verify_confirm] pending 데이터 없음 또는 TTL 만료 (callback_id=%s)",
            data.callback_id,
        )

    birth_date = (
        extract_birth_date(pending["jumin"], callback_id=data.callback_id)
        if pending and pending.get("jumin")
        else None
    )
    del_verify_pending(data.callback_id)

    register_data = RegisterRequest(
        name=data.name,
        license_number=data.license_number,
        password=data.password,
        clinic_name=data.clinic_name,
        clinic_address=data.clinic_address,
        clinic_phone=data.clinic_phone,
    )
    doctor = await service.register_doctor(db, register_data, birth_date=birth_date)
    approved = await service.approve_doctor(db, UUID(str(doctor.id)))
    token = service.create_access_token(
        UUID(str(approved["doctor"].id)),
        UUID(str(approved["doctor"].hospital_id)),
        str(approved["doctor"].role),
    )
    return TokenResponse(access_token=token, expires_in=settings.JWT_EXPIRE_MINUTES * 60)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest,request:Request, db: AsyncSession = Depends(get_db)):
    FAIL_KEY = f"login_fail:{data.license_number}"
    LOCK_KEY = f"login_lock:{data.license_number}"
    PW_EXPIRE_DAYS = 90

    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    if _redis:
        is_locked = _redis.get(LOCK_KEY)
        if is_locked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="비밀번호 5회 오류로 계정이 잠겼습니다. 30분 후 재시도하거나 관리자에게 문의하세요.",
            )

    doctor = await service.get_doctor_by_license(db, data.license_number)
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="등록되지 않은 면허번호입니다.",
        )

    is_verified = service.pwd_context.verify(data.password, str(doctor.password_hash))
    if not is_verified:
        login_log = LoginLog(
            success = False,
            ip_address = ip,
            account_type = "doctor",
            account_id = doctor.id,
            user_agent = ua,
            action = "로그인 실패",
        )
        db.add(login_log)
        await db.commit()
        if _redis:
            fail_count = _redis.incr(FAIL_KEY)
            _redis.expire(FAIL_KEY, LOCK_SECONDS)
            if fail_count >= MAX_FAIL:
                _redis.set(LOCK_KEY, "1", ex=LOCK_SECONDS)
                _redis.delete(FAIL_KEY)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="비밀번호 5회 오류로 계정이 잠겼습니다. 30분 후 재시도하거나 관리자에게 문의하세요.",
                )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"비밀번호가 일치하지 않습니다. (남은 시도: {MAX_FAIL - fail_count}회)",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="비밀번호가 일치하지 않습니다.",
        )

    if _redis:
        _redis.delete(FAIL_KEY)

    if not bool(doctor.is_approved):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="승인 대기 중입니다.",
        )
    if not bool(doctor.is_active):
        raise HTTPException(
            status_code=403,
            detail="비활성화된 계정입니다."
        )

    force_password_change = bool(doctor.force_password_change)
    if not force_password_change and doctor.password_changed_at:
        if datetime.now(timezone.utc) - doctor.password_changed_at > timedelta(days=PW_EXPIRE_DAYS):
            force_password_change = True

    subscription = await get_subscription(db, doctor)
    tier = subscription.tier if subscription else "basic"
    login_log  = LoginLog(
            success = True,
            ip_address = ip,
            account_type = "doctor",
            account_id = doctor.id,
            user_agent = ua,
            action = "로그인",
    )
    token = service.create_access_token(
        UUID(str(doctor.id)), UUID(str(doctor.hospital_id)), str(doctor.role)
    )
    allowed = await add_session(
        str(doctor.hospital_id), token, str(tier), settings.JWT_EXPIRE_MINUTES * 60
    )
    if not allowed:
        raise HTTPException(status_code=429, detail="이미 다른 기기에서 로그인 중입니다.")
    db.add(login_log)
    await db.commit()

    return TokenResponse(
        access_token=token,
        expires_in=settings.JWT_EXPIRE_MINUTES * 60,
        force_password_change=force_password_change,
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    token = credentials.credentials
    from jose import jwt as jose_jwt
    payload = jose_jwt.decode(
        token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )
    hospital_id = payload.get("hospital_id")
    await add_token_blacklist(token, expire_seconds=settings.JWT_EXPIRE_MINUTES * 60)
    if hospital_id:
        await remove_session(hospital_id, token)

    account_id = payload.get("sub")
    role = payload.get("role")
    if account_id:
        db.add(LoginLog(
            success=True,
            ip_address=request.client.host if request.client else None,
            account_type="doctor" if role in ("owner", "associate") else "staff",
            account_id=UUID(account_id),
            user_agent=request.headers.get("user-agent"),
            action="로그아웃",
        ))
        await db.commit()

    return {"message": "로그아웃되었습니다."}


@router.put("/password", status_code=status.HTTP_200_OK)
async def change_password(
    data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    user: Union[Doctor, StaffAccount] = Depends(get_current_user),
):
    account_type = "doctor" if isinstance(user, Doctor) else "staff"
    if not service.pwd_context.verify(data.current_password, str(user.password_hash)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="현재 비밀번호가 일치하지 않습니다.",
        )
    if await service.check_password_history(db, account_type, user.id, data.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="최근 사용한 비밀번호는 다시 사용할 수 없습니다.",
        )
    user.password_hash = service.pwd_context.hash(data.new_password)
    user.password_changed_at = datetime.now(timezone.utc)
    user.force_password_change = False
    await service.save_password_history(db, account_type, user.id, str(user.password_hash))
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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="유효하지 않은 관리자 키입니다.")
    result = await service.approve_doctor(db, doctor_id)
    doctor = result["doctor"]
    return AdminApproveResponse(
        doctor_id=doctor.id,
        name=str(doctor.name),
        access_token=result["access_token"],
        approved_at=doctor.approved_at,
    )


@router.patch("/admin/doctors/{doctor_id}/deactivate")
async def admin_deactivate_doctor(
    doctor_id: UUID,
    db: AsyncSession = Depends(get_db),
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
):
    if x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="유효하지 않은 관리자 키입니다.")
    doctor = await service.deactivate_doctor(db, doctor_id)
    await service.record_access_control_log(
        db,
        hospital_id=UUID(str(doctor.hospital_id)),
        target_account_id=UUID(str(doctor.id)),
        target_account_type="doctor",
        role=str(doctor.role),
        action_type="말소",
        reason="퇴사",
        acted_by=None,
    )
    await db.commit()
    return {"doctor_id": doctor.id, "name": doctor.name, "is_active": doctor.is_active}


@router.post("/admin/unlock/{license_number}")
async def unlock_account(
    license_number: str,
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
):
    if x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="권한 없음")
    if _redis:
        _redis.delete(f"login_lock:{license_number}")
        _redis.delete(f"login_fail:{license_number}")
    return {"message": f"{license_number} 계정 잠금 해제 완료"}


@router.get("/me")
async def get_me(
    user: Union[Doctor, StaffAccount] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    hospital_result = await db.execute(
        select(Hospital).where(Hospital.id == user.hospital_id)
    )
    hospital = hospital_result.scalar_one_or_none()
    institution_code = hospital.institution_code if hospital else None
    agency_code = hospital.agency_code if hospital else None
    approval_no = hospital.approval_no if hospital else None

    last_login_result = await db.execute(
        select(LoginLog)
        .where(LoginLog.account_id == user.id, LoginLog.success == True)  # noqa: E712
        .order_by(LoginLog.attempted_at.desc())
        .offset(1)
        .limit(1)
    )
    last_login = last_login_result.scalar_one_or_none()
    last_login_ip = last_login.ip_address if last_login else None
    last_login_at = (
        last_login.attempted_at.strftime("%Y%m%d%H%M%S")
        if last_login and last_login.attempted_at
        else None
    )

    if isinstance(user, Doctor):
        subscription_result = await db.execute(select(Subscription).where(Subscription.hospital_id == hospital.id ))
        subscription = subscription_result.scalar_one_or_none()

        return {
            "id": user.id,
            "name": user.name,
            "license_number": user.license_number,
            "role": user.role,
            "hospital_id": user.hospital_id,
            "hospital_name": hospital.name if hospital else None,
            "institution_code": institution_code,
            "agency_code": agency_code,
            "approval_no": approval_no,
            "birth_date": user.birth_date,
            "tier" :  subscription.tier,
            "expired_at" : subscription.expired_at,
            "is_expired": (
                subscription.expired_at is None or 
                subscription.expired_at < datetime.now(timezone.utc)
            ) if subscription else True,
            "chuna_training_certified": user.chuna_training_certified,
            "chuna_training_banner_seen": user.chuna_training_banner_seen,
            "last_login_ip": last_login_ip,
            "last_login_at": last_login_at,
        }
    return {
        "id": user.id,
        "name": user.name,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "hospital_id": user.hospital_id,
        "hospital_name": hospital.name if hospital else None,
        "institution_code": institution_code,
        "agency_code": agency_code,
        "approval_no": approval_no,
        "last_login_ip": last_login_ip,
        "last_login_at": last_login_at,
    }


@router.patch("/me")
async def update_me(
    data: DoctorProfileUpdate,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    if data.birth_date is not None:
        doctor.birth_date = data.birth_date
    if data.chuna_training_certified is not None:
        doctor.chuna_training_certified = data.chuna_training_certified
    if data.chuna_training_banner_seen is not None:
        doctor.chuna_training_banner_seen = data.chuna_training_banner_seen
    await db.commit()
    return {
        "birth_date": doctor.birth_date,
        "chuna_training_certified": doctor.chuna_training_certified,
        "chuna_training_banner_seen": doctor.chuna_training_banner_seen,
    }


@router.post("/staff/login", response_model=TokenResponse)
async def staff_login(data: StaffLoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    FAIL_KEY = f"login_fail:staff:{data.username}"
    LOCK_KEY = f"login_lock:staff:{data.username}"

    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    if _redis:
        is_locked = _redis.get(LOCK_KEY)
        if is_locked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="비밀번호 5회 오류로 계정이 잠겼습니다. 30분 후 재시도하거나 관리자에게 문의하세요.",
            )

    staff = await service.get_staff_by_username(db, data.username)
    if staff is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="등록되지 않은 아이디입니다.",
        )

    is_verified = service.pwd_context.verify(data.password, str(staff.password_hash))
    if not is_verified:
        login_log = LoginLog(
            success = False,
            ip_address = ip,
            account_type = "staff",
            account_id = staff.id,
            user_agent = ua,
            action = "로그인 실패",
        )
        db.add(login_log)
        await db.commit()
        if _redis:
            fail_count = _redis.incr(FAIL_KEY)
            _redis.expire(FAIL_KEY, LOCK_SECONDS)
            if fail_count >= MAX_FAIL:
                _redis.set(LOCK_KEY, "1", ex=LOCK_SECONDS)
                _redis.delete(FAIL_KEY)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="비밀번호 5회 오류로 계정이 잠겼습니다. 30분 후 재시도하거나 관리자에게 문의하세요.",
                )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"비밀번호가 일치하지 않습니다. (남은 시도: {MAX_FAIL - fail_count}회)",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="비밀번호가 일치하지 않습니다.",
        )

    if _redis:
        _redis.delete(FAIL_KEY)

    if not bool(staff.is_active):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다.",
        )

    PW_EXPIRE_DAYS = 90
    force_password_change = bool(staff.force_password_change)
    if not force_password_change and staff.password_changed_at:
        if datetime.now(timezone.utc) - staff.password_changed_at > timedelta(days=PW_EXPIRE_DAYS):
            force_password_change = True

    login_log = LoginLog(
            success = True,
            ip_address = ip,
            account_type = "staff",
            account_id = staff.id,
            user_agent = ua,
            action = "로그인",
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
        raise HTTPException(status_code=429, detail="이미 다른 기기에서 로그인 중입니다.")
    db.add(login_log)
    await db.commit()

    return TokenResponse(
        access_token=token,
        expires_in=settings.JWT_EXPIRE_MINUTES * 60,
        force_password_change=force_password_change,
    )




@router.get("/login-logs", )
async def get_login_logs(db:AsyncSession=Depends(get_db),
                            user: Union[Doctor, StaffAccount] = Depends(get_current_user),
                        ):
    if user.role != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="오너 계정만 접근 가능합니다.")
    doctor_ids = (await db.execute(
        select(Doctor.id).where(Doctor.hospital_id == user.hospital_id)
    )).scalars().all()

    staff_ids = (await db.execute(
        select(StaffAccount.id).where(StaffAccount.hospital_id == user.hospital_id)
    )).scalars().all()

    all_ids = list(doctor_ids) + list(staff_ids)

    result = await db.execute(
        select(LoginLog)
        .where(LoginLog.account_id.in_(all_ids))
        .order_by(LoginLog.attempted_at.desc())
    )
    logs = result.scalars().all()
    return [
        {
            "id": str(log.id),
            "account_id": str(log.account_id),
            "account_type": log.account_type,
            "success": log.success,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "attempted_at": log.attempted_at.strftime("%Y%m%d%H%M%S") if log.attempted_at else None,
            "action": log.action,
        }
        for log in logs
    ]


@router.get("/account-histories")
async def get_account_histories(db:AsyncSession=Depends(get_db),
                            user: Union[Doctor, StaffAccount] = Depends(get_current_user),
                        ):
    if user.role != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="오너 계정만 접근 가능합니다.")
    doctor_ids = (await db.execute(
        select(Doctor.id).where(Doctor.hospital_id == user.hospital_id)
    )).scalars().all()

    staff_ids = (await db.execute(
        select(StaffAccount.id).where(StaffAccount.hospital_id == user.hospital_id)
    )).scalars().all()

    all_ids = list(doctor_ids) + list(staff_ids)

    result = await db.execute(select(AccountHistory)
.where(AccountHistory.account_id.in_(all_ids))
.order_by(AccountHistory.started_at.desc()))
    return result.scalars().all()


@router.get("/access-control-logs")
async def get_access_control_logs(
    db: AsyncSession = Depends(get_db),
    user: Union[Doctor, StaffAccount] = Depends(get_current_user),
):
    """접근권한 부여/변경/말소 이력. 오너 계정만, 자기 병원 데이터만 조회 가능."""
    if user.role != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="오너 계정만 접근 가능합니다.")

    result = await db.execute(
        select(AccessControlLog)
        .where(AccessControlLog.hospital_id == user.hospital_id)
        .order_by(AccessControlLog.acted_at.desc())
    )
    logs = result.scalars().all()

    doctor_rows = (await db.execute(
        select(Doctor.id, Doctor.name).where(Doctor.hospital_id == user.hospital_id)
    )).all()
    staff_rows = (await db.execute(
        select(StaffAccount.id, StaffAccount.name).where(StaffAccount.hospital_id == user.hospital_id)
    )).all()
    name_map = {str(i): n for i, n in [*doctor_rows, *staff_rows]}

    return [
        {
            "id": str(log.id),
            "target_account_id": str(log.target_account_id),
            "target_account_name": name_map.get(str(log.target_account_id)),
            "target_account_type": log.target_account_type,
            "role": log.role,
            "action_type": log.action_type,
            "reason": log.reason,
            "acted_at": log.acted_at,
            "acted_by": str(log.acted_by) if log.acted_by else None,
            "acted_by_name": name_map.get(str(log.acted_by)) if log.acted_by else None,
        }
        for log in logs
    ]


@router.get("/audit-logs")
async def get_audit_logs(
    table_name: str | None = Query(None, description="patients / medical_records 등 테이블명 필터"),
    action: str | None = Query(None, description="create / update / delete 등"),
    start_date: str | None = Query(None, description="YYYYMMDD, changed_at 시작 범위"),
    end_date: str | None = Query(None, description="YYYYMMDD, changed_at 종료 범위"),
    limit: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    user: Union[Doctor, StaffAccount] = Depends(get_current_user),
):
    """개인정보(환자·진료기록 등) 조회·변경 이력. 오너 계정만 접근 가능."""
    if user.role != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="오너 계정만 접근 가능합니다.")

    doctor_ids = (await db.execute(
        select(Doctor.id).where(Doctor.hospital_id == user.hospital_id)
    )).scalars().all()
    staff_ids = (await db.execute(
        select(StaffAccount.id).where(StaffAccount.hospital_id == user.hospital_id)
    )).scalars().all()
    all_ids = list(doctor_ids) + list(staff_ids)

    stmt = select(AuditLog).where(AuditLog.actor_id.in_(all_ids))
    if table_name:
        stmt = stmt.where(AuditLog.table_name == table_name)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if start_date:
        stmt = stmt.where(AuditLog.changed_at >= start_date + "000000")
    if end_date:
        stmt = stmt.where(AuditLog.changed_at <= end_date + "235959")
    stmt = stmt.order_by(AuditLog.changed_at.desc()).limit(limit)

    result = await db.execute(stmt)
    return result.scalars().all()
