from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.core.models import Subscription
from fastapi import HTTPException, status
from datetime import datetime, timezone

from app.core.models import Doctor


async def get_subscription(db: AsyncSession, doctor: Doctor):
    result = await db.execute(
        select(Subscription).where(Subscription.hospital_id == doctor.hospital_id)
    )
    return result.scalar_one_or_none()


async def get_subscription_or_404(db: AsyncSession, doctor: Doctor):
    subscription = await get_subscription(db, doctor)
    if subscription is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="구독 정보가 없습니다."
        )
    return subscription


def check_subscription_active(subscription: Subscription) -> bool:
    is_active = subscription.status == "active"
    expired_at_ok = (
        subscription.expired_at is None or subscription.expired_at >= datetime.now()
    )
    return bool(is_active and expired_at_ok)
