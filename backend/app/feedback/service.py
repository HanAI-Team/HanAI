from uuid import UUID
import httpx
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.models import Feedback, AIResult
from app.core.config import settings
from sqlalchemy import select
from app.core.discord import notify_discord


async def create_feedback(db: AsyncSession, doctor_id: UUID, data) -> Feedback:
    result = await db.execute(
        select(AIResult).where(AIResult.medical_record_id == data.medical_record_id)
    )
    ai_result = result.scalar_one_or_none()
    if not ai_result:
        raise HTTPException(status_code=404, detail="진단 결과를 찾을 수 없습니다.")
    existing = await db.execute(
        select(Feedback).where(
            Feedback.ai_result_id == ai_result.id,
            Feedback.doctor_id == doctor_id,
        )
    )
    if existing.scalars().first():
        raise HTTPException(status_code=409, detail="이미 피드백을 제출했습니다.")
    feedback = Feedback(
        ai_result_id=ai_result.id,
        doctor_id=doctor_id,
        category="overall",
        score=5 if data.is_helpful else 1,
        comment=data.comment,
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    await notify_discord(
        f"📊 피드백 수신\n"
        f"결과: {'👍 도움됨' if data.is_helpful else '👎 도움 안 됨'}\n"
        f"코멘트: {data.comment or '없음'}\n"
        f"진료 기록 ID: {data.medical_record_id}"
    )
    return feedback
