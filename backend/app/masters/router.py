from typing import Optional

from app.billing.schema import (
    ClaimRejectionCodeCreate,
    DrugMasterCreate,
    DrugMasterResponse,
    DrugMasterUpdate,
    FeeCreate,
    FeeItem,
    FeeUpdate,
)
from app.core.database import get_db
from app.core.deps import get_current_doctor
from app.core.models import ClaimRejectionCode, Doctor, DrugMaster, FeeMaster
from app.core.timezone import today_kst
from app.masters.schema import (
    ClaimRejectionCodeItem,
    DrugListResponse,
    FeeListResponse,
    RejectionCodeListResponse,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["masters"])


def _require_owner(doctor: Doctor) -> None:
    if doctor.role != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="오너 계정만 접근 가능합니다.")


def _fee_to_item(r: FeeMaster) -> FeeItem:
    return FeeItem(
        code=r.code,
        name=r.name,
        category=r.category,
        insured_health=r.insured_health,
        insured_medical_aid=r.insured_medical_aid,
        insured_veterans=r.insured_veterans,
        unit_price=r.unit_price,
        is_insured=r.is_insured,
        is_standalone=r.is_standalone,
        effective_date=r.effective_date,
        expired_date=r.expired_date,
    )


# ================================================================
# 수가 마스터 (fee_master)
# ================================================================
@router.get("/fees", response_model=FeeListResponse)
async def list_fees(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="코드 또는 명칭 검색"),
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    stmt = select(FeeMaster)
    if search:
        stmt = stmt.where(
            or_(FeeMaster.code.ilike(f"%{search}%"), FeeMaster.name.ilike(f"%{search}%"))
        )
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = stmt.order_by(FeeMaster.category, FeeMaster.code).offset((page - 1) * size).limit(size)
    rows = (await db.execute(stmt)).scalars().all()
    return FeeListResponse(total=total, page=page, size=size, items=[_fee_to_item(r) for r in rows])


@router.get("/fees/{code}", response_model=FeeItem)
async def get_fee(
    code: str,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    result = await db.execute(select(FeeMaster).where(FeeMaster.code == code))
    fee = result.scalar_one_or_none()
    if not fee:
        raise HTTPException(status_code=404, detail="수가 코드를 찾을 수 없습니다.")
    return _fee_to_item(fee)


@router.post("/fees", response_model=FeeItem, status_code=201)
async def create_fee(
    body: FeeCreate,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    _require_owner(doctor)
    existing = await db.execute(select(FeeMaster).where(FeeMaster.code == body.code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="이미 존재하는 행위코드입니다.")
    fee = FeeMaster(**body.model_dump())
    db.add(fee)
    await db.commit()
    await db.refresh(fee)
    return _fee_to_item(fee)


@router.patch("/fees/{code}", response_model=FeeItem)
async def update_fee(
    code: str,
    body: FeeUpdate,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    _require_owner(doctor)
    result = await db.execute(select(FeeMaster).where(FeeMaster.code == code))
    fee = result.scalar_one_or_none()
    if not fee:
        raise HTTPException(status_code=404, detail="수가 코드를 찾을 수 없습니다.")
    update_fields = body.model_dump(exclude_none=True)
    # 단가가 실제로 바뀌는데 effective_date가 생략됐거나 기존 값 그대로 다시
    # 제출됐으면 오늘 날짜로 자동 기록 (EDI 레코드3 "변경일" 필드 산정 근거).
    if "unit_price" in update_fields and update_fields["unit_price"] != fee.unit_price:
        submitted_effective = update_fields.get("effective_date")
        if submitted_effective is None or submitted_effective == fee.effective_date:
            update_fields["effective_date"] = today_kst()
    for field, value in update_fields.items():
        setattr(fee, field, value)
    await db.commit()
    await db.refresh(fee)
    return _fee_to_item(fee)


@router.delete("/fees/{code}", status_code=204)
async def delete_fee(
    code: str,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    _require_owner(doctor)
    result = await db.execute(select(FeeMaster).where(FeeMaster.code == code))
    fee = result.scalar_one_or_none()
    if not fee:
        raise HTTPException(status_code=404, detail="수가 코드를 찾을 수 없습니다.")
    await db.delete(fee)
    await db.commit()


# ================================================================
# 약가 마스터 (drug_master)
# ================================================================
@router.get("/drugs", response_model=DrugListResponse)
async def list_drugs(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="제품코드, 제품명 또는 주성분명 검색"),
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    stmt = select(DrugMaster)
    if search:
        stmt = stmt.where(
            or_(
                DrugMaster.product_code.ilike(f"%{search}%"),
                DrugMaster.product_name.ilike(f"%{search}%"),
                DrugMaster.ingredient_name.ilike(f"%{search}%"),
            )
        )
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = (
        stmt.order_by(DrugMaster.product_name).offset((page - 1) * size).limit(size)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return DrugListResponse(total=total, page=page, size=size, items=list(rows))


@router.get("/drugs/{code}", response_model=DrugMasterResponse)
async def get_drug(
    code: str,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    result = await db.execute(select(DrugMaster).where(DrugMaster.product_code == code))
    drug = result.scalar_one_or_none()
    if not drug:
        raise HTTPException(status_code=404, detail="제품코드를 찾을 수 없습니다.")
    return drug


@router.post("/drugs", response_model=DrugMasterResponse, status_code=201)
async def create_drug(
    body: DrugMasterCreate,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    _require_owner(doctor)
    existing = await db.execute(
        select(DrugMaster).where(DrugMaster.product_code == body.product_code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="이미 존재하는 제품코드입니다.")
    drug = DrugMaster(**body.model_dump())
    db.add(drug)
    await db.commit()
    await db.refresh(drug)
    return drug


@router.patch("/drugs/{code}", response_model=DrugMasterResponse)
async def update_drug(
    code: str,
    body: DrugMasterUpdate,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    _require_owner(doctor)
    result = await db.execute(select(DrugMaster).where(DrugMaster.product_code == code))
    drug = result.scalar_one_or_none()
    if not drug:
        raise HTTPException(status_code=404, detail="제품코드를 찾을 수 없습니다.")
    update_fields = body.model_dump(exclude_none=True)
    if "unit_price" in update_fields and update_fields["unit_price"] != drug.unit_price:
        submitted_effective = update_fields.get("effective_date")
        if submitted_effective is None or submitted_effective == drug.effective_date:
            update_fields["effective_date"] = today_kst()
    for field, value in update_fields.items():
        setattr(drug, field, value)
    await db.commit()
    await db.refresh(drug)
    return drug


@router.delete("/drugs/{code}", status_code=204)
async def delete_drug(
    code: str,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    _require_owner(doctor)
    result = await db.execute(select(DrugMaster).where(DrugMaster.product_code == code))
    drug = result.scalar_one_or_none()
    if not drug:
        raise HTTPException(status_code=404, detail="제품코드를 찾을 수 없습니다.")
    await db.delete(drug)
    await db.commit()


# ================================================================
# 반송·심사불능 코드 (claim_rejection_codes)
# ================================================================
@router.get("/rejection-codes", response_model=RejectionCodeListResponse)
async def list_rejection_codes(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None, description="반송 | 심사불능 | 수탁기관통보"),
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    stmt = select(ClaimRejectionCode)
    if category:
        stmt = stmt.where(ClaimRejectionCode.category == category)
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = (
        stmt.order_by(
            ClaimRejectionCode.category, ClaimRejectionCode.code, ClaimRejectionCode.detail_code
        )
        .offset((page - 1) * size)
        .limit(size)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return RejectionCodeListResponse(total=total, page=page, size=size, items=list(rows))


@router.post("/rejection-codes", response_model=ClaimRejectionCodeItem, status_code=201)
async def create_rejection_code(
    body: ClaimRejectionCodeCreate,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    _require_owner(doctor)
    existing = await db.execute(
        select(ClaimRejectionCode).where(
            ClaimRejectionCode.category == body.category,
            ClaimRejectionCode.code == body.code,
            ClaimRejectionCode.detail_code == body.detail_code,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="이미 존재하는 코드입니다.")
    item = ClaimRejectionCode(**body.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/rejection-codes/{item_id}", status_code=204)
async def delete_rejection_code(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    _require_owner(doctor)
    item = await db.get(ClaimRejectionCode, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="코드를 찾을 수 없습니다.")
    await db.delete(item)
    await db.commit()
