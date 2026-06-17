from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_doctor
from app.core.models import AcupuncturePoint
from app.acupuncture.schema import (
    AcupuncturePointResponse,
    ConcurrentCheckRequest,
    ConcurrentCheckResponse,
)

router = APIRouter(tags=["acupuncture"])


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
    """단독침술 동시시술 점검 — is_standalone인 경혈이 2개 이상이면 청구 불가."""
    if not body.codes:
        return ConcurrentCheckResponse(valid=True, conflicting_codes=[], message="점검할 경혈이 없습니다.")

    upper_codes = [c.upper() for c in body.codes]
    result = await db.execute(
        select(AcupuncturePoint).where(
            AcupuncturePoint.code.in_(upper_codes),
            AcupuncturePoint.is_standalone.is_(True),
        )
    )
    standalone_points = result.scalars().all()

    if len(standalone_points) > 1:
        conflicting = [p.code for p in standalone_points]
        return ConcurrentCheckResponse(
            valid=False,
            conflicting_codes=conflicting,
            message=f"단독침술 항목 {conflicting}은 동일 회차에 동시 청구할 수 없습니다.",
        )

    return ConcurrentCheckResponse(valid=True, conflicting_codes=[], message="동시시술 점검 통과.")
