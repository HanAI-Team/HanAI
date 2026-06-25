from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_doctor
from app.core.models import KcdUCode
from app.kcd.schema import KcdUCodeResponse, KcdValidateRequest, KcdValidateResponse, KcdValidateResult

router = APIRouter(tags=["kcd"])


@router.post("/validate", response_model=KcdValidateResponse)
async def validate_kcd_codes(
    body: KcdValidateRequest,
    current_doctor=Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
):
    """상병코드 완전코드 여부 검증.

    - 마스터 존재 여부 + 유효기간 체크
    - 환자 성별과 상병코드 sex_restriction 불일치 체크
    - 법정감염병 여부 반환
    """
    ref_date = body.as_of or date.today()
    results = []

    for raw_code in body.codes:
        code = raw_code.strip().upper()

        result = await db.execute(
            select(KcdUCode).where(
                KcdUCode.code == code,
                or_(KcdUCode.effective_date.is_(None), KcdUCode.effective_date <= ref_date),
                or_(KcdUCode.expired_date.is_(None), KcdUCode.expired_date >= ref_date),
            )
        )
        item = result.scalar_one_or_none()

        if item:
            # 성별 제한 체크
            if (
                body.patient_gender
                and item.sex_restriction
                and item.sex_restriction != body.patient_gender
            ):
                gender_label = "남성" if item.sex_restriction == "M" else "여성"
                results.append(KcdValidateResult(
                    code=code,
                    is_valid=False,
                    korean_name=item.korean_name,
                    is_notifiable=item.is_notifiable,
                    error=f"'{code}'는 {gender_label} 전용 상병코드입니다.",
                ))
            else:
                results.append(KcdValidateResult(
                    code=code,
                    is_valid=True,
                    korean_name=item.korean_name,
                    is_notifiable=item.is_notifiable,
                ))
        else:
            # 존재하지 않는 코드 vs 만료 코드 구분
            result_any = await db.execute(
                select(KcdUCode).where(KcdUCode.code == code)
            )
            exists = result_any.scalar_one_or_none()

            if exists:
                error_msg = f"'{code}'는 유효기간이 만료된 상병코드입니다."
            else:
                error_msg = f"'{code}'는 존재하지 않는 상병코드입니다."

            results.append(KcdValidateResult(
                code=code,
                is_valid=False,
                error=error_msg,
            ))

    return KcdValidateResponse(
        results=results,
        has_error=any(not r.is_valid for r in results),
    )


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
