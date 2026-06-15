from uuid import UUID

from fastapi import HTTPException, status
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import StaffAccount, Subscription
from app.staff.schema import StaffCreateRequest

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def create_staff(
    db: AsyncSession, hospital_id: UUID, data: StaffCreateRequest
) -> StaffAccount:
    # 1. staff_limit 체크
    # 2. 이메일 중복 체크
    # 3. StaffAccount 생성
    hosipital_result = await db.execute(
        select(Subscription).where(Subscription.hospital_id == hospital_id)
    )

    hosipital_subcription = hosipital_result.scalar_one_or_none()
    result = await db.execute(
        select(StaffAccount).where(StaffAccount.hospital_id == hospital_id)
    )

    staff_accounts = result.scalars().all()

    if not hosipital_subcription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="구독정보가 없습니다."
        )

    if int(hosipital_subcription.staff_limit or 0) <= len(staff_accounts):  # type: ignore
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="하위 계정 생성 한도를 초과했습니다.",
        )

    username_result = await db.execute(
        select(StaffAccount).where(StaffAccount.username == data.username)
    )
    if username_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="이미 사용 중인 아이디입니다."
        )

    if data.email:
        email_result = await db.execute(
            select(StaffAccount).where(StaffAccount.email == data.email)
        )
        if email_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="이미 사용 중인 이메일입니다."
            )

    staff_account = StaffAccount(
        hospital_id=hospital_id,
        name=data.name,
        username=data.username,
        email=data.email,
        role=data.role,
        password_hash=pwd_context.hash(data.password),
    )
    db.add(staff_account)

    await db.commit()
    await db.refresh(staff_account)

    return staff_account


async def get_staff_list(db: AsyncSession, hospital_id: UUID) -> list[StaffAccount]:
    # hospital_id로 staff 목록 조회
    result = await db.execute(
        select(StaffAccount).where(StaffAccount.hospital_id == hospital_id)
    )
    staff_accounts = result.scalars().all()
    return list(staff_accounts)


async def deactivate_staff(
    db: AsyncSession, hospital_id: UUID, staff_id: UUID
) -> StaffAccount:
    result = await db.execute(
        select(StaffAccount).where(
            StaffAccount.hospital_id == hospital_id, StaffAccount.id == staff_id
        )
    )
    staff_account = result.scalar_one_or_none()
    if not staff_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="등록된 계정이 없습니다."
        )
    staff_account.is_active = False  # type: ignore
    await db.commit()
    await db.refresh(staff_account)
    return staff_account


async def activate_staff(
    db: AsyncSession, hospital_id: UUID, staff_id: UUID
) -> StaffAccount:
    result = await db.execute(
        select(StaffAccount).where(
            StaffAccount.hospital_id == hospital_id, StaffAccount.id == staff_id
        )
    )
    staff_account = result.scalar_one_or_none()
    if not staff_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="등록된 계정이 없습니다."
        )
    staff_account.is_active = True  # type: ignore
    await db.commit()
    await db.refresh(staff_account)
    return staff_account
