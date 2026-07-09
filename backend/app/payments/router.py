
from app.core.database import get_db
from app.core.deps import get_current_user
from app.payments import service
from app.payments.schema import (
    PaymentConfirmRequest,
    PaymentConfirmResponse,
    PaymentPrepareRequest,
    PaymentPrepareResponse,
)
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/payments", tags=["payments"])


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