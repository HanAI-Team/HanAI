from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_doctor
from app.core.models import KcdUCode
from app.kcd.schema import KcdUCodeResponse

router = APIRouter(tags=["kcd"])


@router.get("/search", response_model=List[KcdUCodeResponse])
async def search_kcd_codes(
    q: str = Query(..., min_length=1, description="코드 또는 한글명 검색어"),
    category: Optional[str] = Query(None, description="카테고리 필터"),
    as_of: Optional[date] = Query(None, description="적용일자 기준 (기본: 오늘)"),
    limit: int = Query(20, ge=1, le=100),
    current_doctor=Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
):
    ref_date = as_of or date.today()
    stmt = select(KcdUCode).where(
        or_(
            KcdUCode.code.ilike(f"{q}%"),
            KcdUCode.korean_name.ilike(f"%{q}%"),
            KcdUCode.hanja.ilike(f"%{q}%"),
        )
    )
    if category:
        stmt = stmt.where(KcdUCode.category == category)
    # effective_date가 있으면 ref_date 이전이어야 함, expired_date가 있으면 ref_date 이후여야 함
    stmt = stmt.where(
        and_(
            or_(KcdUCode.effective_date.is_(None), KcdUCode.effective_date <= ref_date),
            or_(KcdUCode.expired_date.is_(None), KcdUCode.expired_date >= ref_date),
        )
    )
    stmt = stmt.order_by(KcdUCode.code).limit(limit)

    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/categories", response_model=List[str])
async def list_categories(
    current_doctor=Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(KcdUCode.category).distinct().order_by(KcdUCode.category)
    )
    return [r for r in result.scalars().all() if r]


@router.get("/{code}", response_model=KcdUCodeResponse)
async def get_kcd_code(
    code: str,
    as_of: Optional[date] = Query(None, description="적용일자 기준 (기본: 오늘)"),
    current_doctor=Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
):
    ref_date = as_of or date.today()
    result = await db.execute(
        select(KcdUCode).where(
            KcdUCode.code == code.upper(),
            or_(KcdUCode.effective_date.is_(None), KcdUCode.effective_date <= ref_date),
            or_(KcdUCode.expired_date.is_(None), KcdUCode.expired_date >= ref_date),
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail=f"코드 '{code}'를 찾을 수 없습니다.")
    return item
