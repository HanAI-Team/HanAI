from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_doctor
from app.core.models import Doctor
from app.feedback import service
from app.feedback.schema import FeedbackCreate, FeedbackResponse

router = APIRouter(tags=["feedback"])


@router.post("/", response_model=FeedbackResponse)
async def create_feedback(
    data: FeedbackCreate,
    doctor: Doctor = Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
):
    return await service.create_feedback(db, UUID(str(doctor.id)), data)
