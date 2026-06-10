from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_doctor
from app.core.models import Doctor
from app.subscription import service
from app.subscription.schema import SubscriptionResponse

router = APIRouter(tags=["subscription"])


@router.get("/", response_model=SubscriptionResponse)
async def get_subscription(
    db: AsyncSession = Depends(get_db), doctor: Doctor = Depends(get_current_doctor)
):
    subscription = await service.get_subscription_or_404(db, doctor)
    return SubscriptionResponse.model_validate(subscription)
