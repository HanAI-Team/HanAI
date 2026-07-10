import hashlib
import hmac
import logging
from typing import Optional

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.payments import service
from app.payments.schema import (
    PaymentConfirmRequest,
    PaymentConfirmResponse,
    PaymentPrepareRequest,
    PaymentPrepareResponse,
)
from app.payments.schema import TossWebhookPayload
from fastapi import APIRouter, Depends
from fastapi import Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payments", tags=["payments"])

SUPPORTED_TOSS_WEBHOOK_EVENTS = {
    "Payment.DONE",
    "Payment.CANCELED",
    "Payment.FAILED",
    "BillingKey.DELETED",
}


@router.post("/prepare", response_model=PaymentPrepareResponse)
async def prepare_payment(
    body: PaymentPrepareRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await service.prepare_payment(
        db=db,
        hospital_id=current_user.hospital_id,
        tier=body.tier,
        billing_period=body.billing_period,
    )


@router.post("/confirm", response_model=PaymentConfirmResponse)
async def confirm_payment(
    body: PaymentConfirmRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await service.confirm_payment(
        db=db,
        hospital_id=current_user.hospital_id,
        payment_key=body.payment_key,
        order_id=body.order_id,
        amount=body.amount,
    )


@router.post("/webhook/toss")
async def toss_webhook(
    request: Request,
    toss_payments_signature: Optional[str] = Header(default=None, alias="TossPayments-Signature"),
):
    """토스페이먼츠 웹훅 수신. 토스가 호출하는 엔드포인트라 인증 없음 — 대신 서명 검증으로 대체."""
    raw_body = await request.body()

    if not settings.TOSS_WEBHOOK_SECRET or not toss_payments_signature:
        raise HTTPException(status_code=400, detail="invalid signature")

    expected_signature = hmac.new(
        settings.TOSS_WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, toss_payments_signature):
        raise HTTPException(status_code=400, detail="invalid signature")

    payload = TossWebhookPayload.model_validate_json(raw_body)

    if payload.event_type not in SUPPORTED_TOSS_WEBHOOK_EVENTS:
        logger.info("Unsupported toss webhook event_type=%s data=%s", payload.event_type, payload.data)
        return {"received": True}

    logger.info("Toss webhook event_type=%s data=%s", payload.event_type, payload.data)

    if payload.event_type == "Payment.DONE":
        pass  # TODO: 결제 완료 처리
    elif payload.event_type == "Payment.CANCELED":
        pass  # TODO: 결제 취소 처리
    elif payload.event_type == "Payment.FAILED":
        pass  # TODO: 결제 실패 처리
    elif payload.event_type == "BillingKey.DELETED":
        pass  # TODO: 빌링키 삭제 처리

    # 토스 웹훅 재시도 방지를 위해 항상 200 반환 (서명 검증 실패 제외)
    return {"received": True}