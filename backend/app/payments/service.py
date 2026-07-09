import base64
import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from uuid import UUID

import httpx
from app.core.config import settings
from app.core.models import Payment, Subscription
from app.core.redis import get_redis  # 기존 Redis 클라이언트 import 방식 확인 필요
from app.payments.schema import ORDER_NAME_TABLE, TIER_CONFIG
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

_redis = get_redis()


VALID_TIERS = set(TIER_CONFIG.keys())


async def prepare_payment(
        db:AsyncSession,
        hospital_id : UUID,
        tier : str, 
        billing_period:str
) ->dict:
    config = TIER_CONFIG.get((tier, billing_period))
    if not config:
        raise HTTPException(status_code=400, detail="유효하지 않은 플랜입니다.")
    amount  = config["amount"]
    
    order_id = f"ZINMAC-{str(hospital_id)[:8]}-{int(time.time() * 1000)}-{str(uuid.uuid4())[:8]}"



    if _redis:
        _redis.set(
    f"payment:{order_id}",
        json.dumps({
                "tier": tier,
                "billing_period": billing_period,
                "amount": amount,
                "hospital_id": str(hospital_id),
            }),
            ex=600,
        )

    payment = Payment(
        hospital_id=hospital_id,
        order_id=order_id,
        tier=tier,
        billing_period=billing_period,
        amount=amount,
        status="pending", 
    )

    db.add(payment)
    await db.commit()
    return {
        "order_id": order_id,
        "amount": amount,
        "order_name": ORDER_NAME_TABLE[(tier, billing_period)],
    }

async def confirm_payment(
    db: AsyncSession,
    hospital_id: UUID,
    payment_key: str,
    order_id: str,
    amount: int,
) -> dict:
    raw = _redis.get(f"payment:{order_id}") if _redis else None
    if not raw:
        raise HTTPException(
            status_code=400,
            detail="주문 정보가 만료됐거나 존재하지 않습니다.",
        )  
    
    order_data = json.loads(raw)

    if order_data["amount"] != amount:
        raise HTTPException(status_code=400, detail="결제 금액이 일치하지 않습니다.")
    
    credentials = base64.b64encode(
        f"{settings.TOSS_SECRET_KEY}:".encode()
    ).decode()
    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://api.tosspayments.com/v1/payments/confirm",
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/json",
            },
            json={
                "paymentKey": payment_key,
                "orderId": order_id,
                "amount": amount,
            },
        )
    if res.status_code != 200:
        # Payment 실패 기록
        print(f"토스 에러: {res.status_code} {res.text}")

        fail_result = await db.execute(
            select(Payment).where(Payment.order_id == order_id)
        )
        fail_payment = fail_result.scalar_one_or_none()
        if fail_payment:
            fail_payment.status = "failed"
            await db.commit()

        raise HTTPException(status_code=400, detail="결제 승인에 실패했습니다.")
    
    pay_result = await db.execute(select(Payment).where(Payment.order_id == order_id))

    payment = pay_result.scalar_one_or_none()

    if payment:
        payment.status = "paid"
        payment.payment_key = payment_key
        payment.paid_at = datetime.now(timezone.utc)
    tier = order_data["tier"]
    billing_period = order_data["billing_period"]
    display_tier = TIER_CONFIG[(tier, billing_period)]["display_tier"]
    days = 30 if billing_period == "monthly" else 365


    sub_result = await db.execute(
        select(Subscription).where(Subscription.hospital_id == hospital_id)
    )
    subscription = sub_result.scalar_one_or_none()

    if subscription:
        subscription.tier = display_tier
        subscription.status = "active"
        subscription.expired_at = datetime.now(timezone.utc) + timedelta(days=days)
    else:
        # 없으면 새로 생성
        subscription = Subscription(
            hospital_id=hospital_id,
            tier=display_tier,
            status="active",
            started_at=datetime.now(timezone.utc),
            expired_at=datetime.now(timezone.utc) + timedelta(days=days),
        )
        db.add(subscription)
    await db.commit()

    # 7. Redis 키 삭제
    if _redis:
        _redis.delete(f"payment:{order_id}")

    return {
        "success": True,
        "tier": display_tier,
        "billing_period": billing_period,
        "expired_at": subscription.expired_at.isoformat() if subscription else "",
        "message": "결제가 완료됐습니다.",
    }

