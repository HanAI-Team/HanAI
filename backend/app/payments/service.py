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


async def confirm_paddle_payment(
    db: AsyncSession,
    hospital_id: UUID,
    transaction_id: str,
) -> dict:
    """Paddle 결제 확인. 프론트가 넘겨준 transaction_id로 Paddle 서버에 직접 조회해
    결제 상태/금액을 검증한 뒤 구독을 갱신한다 (토스 confirm_payment와 동일한 패턴)."""

    # 이미 처리된 거래면 재처리하지 않고 현재 구독 상태 그대로 반환 (중복 호출 대비)
    existing_result = await db.execute(
        select(Payment).where(Payment.order_id == transaction_id)
    )
    existing_payment = existing_result.scalar_one_or_none()
    if existing_payment and existing_payment.status == "paid":
        sub_result = await db.execute(
            select(Subscription).where(Subscription.hospital_id == hospital_id)
        )
        subscription = sub_result.scalar_one_or_none()
        return {
            "success": True,
            "tier": existing_payment.tier,
            "billing_period": existing_payment.billing_period,
            "expired_at": subscription.expired_at.isoformat()
            if subscription and subscription.expired_at
            else "",
            "message": "이미 처리된 결제입니다.",
        }

    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{settings.PADDLE_API_BASE_URL}/transactions/{transaction_id}",
            headers={"Authorization": f"Bearer {settings.PADDLE_API_KEY}"},
        )
    if res.status_code != 200:
        print(f"Paddle 에러: {res.status_code} {res.text}")
        raise HTTPException(status_code=400, detail="Paddle 거래 정보를 확인할 수 없습니다.")

    txn = res.json().get("data", {})
    if txn.get("status") != "completed":
        raise HTTPException(status_code=400, detail="결제가 완료되지 않았습니다.")

    custom_data = txn.get("custom_data") or {}
    tier = custom_data.get("tier")
    billing_period = custom_data.get("billing_period")
    config = TIER_CONFIG.get((tier, billing_period))
    if not config:
        raise HTTPException(status_code=400, detail="유효하지 않은 결제 정보입니다.")

    # KRW는 소수점 없는 정수 문자열로 청구되므로 그대로 비교
    totals = (txn.get("details") or {}).get("totals") or {}
    paid_amount = int(totals.get("total", 0))
    if paid_amount != config["amount"]:
        raise HTTPException(status_code=400, detail="결제 금액이 일치하지 않습니다.")

    if existing_payment:
        existing_payment.status = "paid"
        existing_payment.payment_key = transaction_id
        existing_payment.paid_at = datetime.now(timezone.utc)
    else:
        db.add(
            Payment(
                hospital_id=hospital_id,
                order_id=transaction_id,
                payment_key=transaction_id,
                tier=tier,
                billing_period=billing_period,
                amount=paid_amount,
                status="paid",
                paid_at=datetime.now(timezone.utc),
            )
        )

    display_tier = config["display_tier"]
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
        subscription = Subscription(
            hospital_id=hospital_id,
            tier=display_tier,
            status="active",
            started_at=datetime.now(timezone.utc),
            expired_at=datetime.now(timezone.utc) + timedelta(days=days),
        )
        db.add(subscription)

    await db.commit()

    return {
        "success": True,
        "tier": display_tier,
        "billing_period": billing_period,
        "expired_at": subscription.expired_at.isoformat(),
        "message": "결제가 완료됐습니다.",
    }

