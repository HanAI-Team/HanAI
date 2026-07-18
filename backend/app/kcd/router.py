from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.csv_export import csv_response
from app.core.database import get_db
from app.core.deps import get_current_doctor
from app.core.models import KcdUCode
from app.core.timezone import today_kst
from app.kcd.schema import (
    KcdCodeCreate,
    KcdCodeUpdate,
    KcdUCodeResponse,
    KcdValidateRequest,
    KcdValidateResponse,
    KcdValidateResult,
)

router = APIRouter(tags=["kcd"])

# K00~K14: ICD-10 "구강, 타액선 및 턱의 질환"(치과 영역). Zinmac은 한의원 전용
# 앱이라 진단 검색 결과에 치과 전용 상병코드가 섞여 나올 이유가 없어 제외한다
# (2026-07-16, 실사용 중 "K0522 급성 치관주위염" 등이 섞여 나온다는 피드백으로
# 확인). K20 이상 일반 소화기 질환(위염 등)은 한의과에서도 다루므로 그대로 둔다.
_EXCLUDED_KCD_PREFIXES = [f"K{i:02d}" for i in range(15)]


def _check_admin(key: str) -> None:
    if key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="관리자 키가 올바르지 않습니다.")


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
    ref_date = body.as_of or today_kst()
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
    ref_date = as_of or today_kst()
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
    stmt = stmt.where(
        ~or_(*(KcdUCode.code.like(f"{prefix}%") for prefix in _EXCLUDED_KCD_PREFIXES))
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


@router.get("/export")
async def export_kcd_codes(
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
    db: AsyncSession = Depends(get_db),
):
    """KCD 상병코드 마스터 전체를 CSV(TEXT/Excel)로 추출.

    ※ /{code} 조회 라우트보다 먼저 등록해야 함 — 아래에 있으면 "export"가
    코드값으로 잘못 매칭됨.
    """
    _check_admin(x_admin_key)
    result = await db.execute(select(KcdUCode).order_by(KcdUCode.code))
    rows = [
        [
            r.code, r.korean_name, r.hanja, r.category,
            r.effective_date, r.expired_date, r.sex_restriction, r.is_notifiable,
        ]
        for r in result.scalars().all()
    ]
    header = [
        "code", "korean_name", "hanja", "category",
        "effective_date", "expired_date", "sex_restriction", "is_notifiable",
    ]
    return csv_response("kcd_codes.csv", header, rows)


@router.get("/{code}", response_model=KcdUCodeResponse)
async def get_kcd_code(
    code: str,
    as_of: Optional[date] = Query(None, description="적용일자 기준 (기본: 오늘)"),
    current_doctor=Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
):
    ref_date = as_of or today_kst()
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


@router.post("", response_model=KcdUCodeResponse, status_code=201)
async def create_kcd_code(
    body: KcdCodeCreate,
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
    db: AsyncSession = Depends(get_db),
):
    _check_admin(x_admin_key)
    existing = await db.execute(select(KcdUCode).where(KcdUCode.code == body.code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="이미 존재하는 상병코드입니다.")
    item = KcdUCode(**body.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.put("/{code}", response_model=KcdUCodeResponse)
async def update_kcd_code(
    code: str,
    body: KcdCodeUpdate,
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
    db: AsyncSession = Depends(get_db),
):
    _check_admin(x_admin_key)
    result = await db.execute(select(KcdUCode).where(KcdUCode.code == code))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail=f"코드 '{code}'를 찾을 수 없습니다.")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(item, field, value)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/{code}", status_code=204)
async def delete_kcd_code(
    code: str,
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
    db: AsyncSession = Depends(get_db),
):
    _check_admin(x_admin_key)
    result = await db.execute(select(KcdUCode).where(KcdUCode.code == code))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail=f"코드 '{code}'를 찾을 수 없습니다.")
    await db.delete(item)
    await db.commit()
