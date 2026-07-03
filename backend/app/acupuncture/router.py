from datetime import datetime, timezone
from typing import List
from uuid import UUID

from app.acupuncture.schema import (
    AcupuncturePointResponse,
    ConcurrentCheckRequest,
    ConcurrentCheckResponse,
    CrossVisitDuplicateCheckRequest,
    CrossVisitDuplicateCheckResponse,
    DailyLimitCheckRequest,
    DailyLimitCheckResponse,
    SpecialLimitCheckRequest,
    SpecialLimitCheckResponse,
)
from app.core.database import get_db
from app.core.deps import get_current_doctor
from app.core.models import AcupuncturePoint, ClaimLineItem, FeeMaster, MedicalRecord
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["acupuncture"])

DAILY_ACUPUNCTURE_LIMIT = 3
SPECIAL_ACUPUNCTURE_LIMIT = 2
SPECIAL_ACUPUNCTURE_CODES = {
    "40030", "40040", "40050", "40060", "40070", "40080", "40100"
}


@router.get("/search", response_model=List[AcupuncturePointResponse])
async def search_acupuncture_points(
    q: str = Query(..., min_length=1, description="경혈 코드 또는 한글명"),
    limit: int = Query(20, ge=1, le=100),
    current_doctor=Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(AcupuncturePoint)
        .where(
            or_(
                AcupuncturePoint.code.ilike(f"{q}%"),
                AcupuncturePoint.korean_name.ilike(f"%{q}%"),
            )
        )
        .order_by(AcupuncturePoint.code)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{code}", response_model=AcupuncturePointResponse)
async def get_acupuncture_point(
    code: str,
    current_doctor=Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AcupuncturePoint).where(AcupuncturePoint.code == code.upper())
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail=f"경혈 코드 '{code}'를 찾을 수 없습니다.")
    return item


@router.post("/check-concurrent", response_model=ConcurrentCheckResponse)
async def check_concurrent_acupuncture(
    body: ConcurrentCheckRequest,
    current_doctor=Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
):
    """분구침술 동시청구 점검 — is_standalone=True인 코드가 2개 이상이면 청구 불가."""
    if not body.codes:
        return ConcurrentCheckResponse(valid=True, conflicting_codes=[], message="점검할 코드가 없습니다.")

    result = await db.execute(
        select(FeeMaster).where(
            FeeMaster.code.in_(body.codes),
            FeeMaster.is_standalone.is_(True),
        )
    )
    standalone_items = result.scalars().all()

    if len(standalone_items) > 1:
        conflicting = [item.code for item in standalone_items]
        return ConcurrentCheckResponse(
            valid=False,
            conflicting_codes=conflicting,
            message=f"분구침술 항목 {conflicting}은 동일 회차에 동시 청구할 수 없습니다.",
        )

    return ConcurrentCheckResponse(valid=True, conflicting_codes=[], message="동시청구 점검 통과.")


@router.post("/check-daily-limit", response_model=DailyLimitCheckResponse)
async def check_daily_acupuncture_limit(
    body: DailyLimitCheckRequest,
    current_doctor=Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
):
    """1일 침술 3종 초과 점검 — category='침술'인 코드가 3종 초과이면 청구 불가."""
    if not body.codes:
        return DailyLimitCheckResponse(valid=True, excess_count=0, message="점검할 코드가 없습니다.")

    result = await db.execute(
        select(FeeMaster).where(
            FeeMaster.code.in_(body.codes),
            FeeMaster.category == "침술",
        )
    )
    acupuncture_items = result.scalars().all()
    count = len(acupuncture_items)

    if count > DAILY_ACUPUNCTURE_LIMIT:
        return DailyLimitCheckResponse(
            valid=False,
            excess_count=count,
            message=f"침술은 1일 {DAILY_ACUPUNCTURE_LIMIT}종 이내로 산정 가능합니다. (현재 {count}종)",
        )

    return DailyLimitCheckResponse(valid=True, excess_count=count, message="1일 침술 종수 점검 통과.")


@router.post("/check-special-limit", response_model=SpecialLimitCheckResponse)
async def check_special_acupuncture_limit(
    body: SpecialLimitCheckRequest,
    current_doctor=Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
):
    """특수침술 2종 초과 점검 — 하-3~하-8, 하-10(40030~40100) 코드가 2종 초과이면 청구 불가."""
    if not body.codes:
        return SpecialLimitCheckResponse(valid=True, excess_count=0, message="점검할 코드가 없습니다.")

    special_codes = [c for c in body.codes if c in SPECIAL_ACUPUNCTURE_CODES]
    count = len(special_codes)

    if count > SPECIAL_ACUPUNCTURE_LIMIT:
        return SpecialLimitCheckResponse(
            valid=False,
            excess_count=count,
            message=f"특수침술은 1일 {SPECIAL_ACUPUNCTURE_LIMIT}종 이내로 산정 가능합니다. (현재 {count}종)",
        )

    return SpecialLimitCheckResponse(valid=True, excess_count=count, message="특수침술 종수 점검 통과.")


@router.post("/check-cross-visit", response_model=CrossVisitDuplicateCheckResponse)
async def check_cross_visit_duplicate(
    body: CrossVisitDuplicateCheckRequest,
    current_doctor=Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
):
    """같은 날 다른 내원 간 분구침술 중복 청구 점검."""
    if not body.codes:
        return CrossVisitDuplicateCheckResponse(
            valid=True, conflicting_codes=[], message="점검할 코드가 없습니다."
        )

    result = await db.execute(
        select(FeeMaster).where(
            FeeMaster.code.in_(body.codes),
            FeeMaster.is_standalone.is_(True),
        )
    )
    standalone_in_request = [item.code for item in result.scalars().all()]

    if not standalone_in_request:
        return CrossVisitDuplicateCheckResponse(
            valid=True, conflicting_codes=[], message="분구침술 코드가 없습니다."
        )

    visit_start = datetime(body.visit_date.year, body.visit_date.month, body.visit_date.day, 0, 0, 0, tzinfo=timezone.utc)
    visit_end = datetime(body.visit_date.year, body.visit_date.month, body.visit_date.day, 23, 59, 59, tzinfo=timezone.utc)

    r_records = await db.execute(
        select(MedicalRecord).where(
            MedicalRecord.patient_id == UUID(body.patient_id),
            MedicalRecord.recorded_at >= visit_start,
            MedicalRecord.recorded_at <= visit_end,
        )
    )
    other_records = r_records.scalars().all()

    if not other_records:
        return CrossVisitDuplicateCheckResponse(
            valid=True, conflicting_codes=[], message="당일 다른 내원 없음."
        )

    other_record_ids = [r.id for r in other_records]
    r_items = await db.execute(
        select(ClaimLineItem).where(
            ClaimLineItem.medical_record_id.in_(other_record_ids),
            ClaimLineItem.code.in_(standalone_in_request),
        )
    )
    conflicting_items = r_items.scalars().all()

    if conflicting_items:
        conflicting = list({item.code for item in conflicting_items})
        return CrossVisitDuplicateCheckResponse(
            valid=False,
            conflicting_codes=conflicting,
            message=f"당일 다른 내원에서 이미 청구된 분구침술 코드가 있습니다: {conflicting}",
        )

    return CrossVisitDuplicateCheckResponse(
        valid=True, conflicting_codes=[], message="당일 중복 청구 없음."
    )
