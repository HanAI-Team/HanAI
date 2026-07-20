"""환자 진료비 수납(ClaimPayment) — 구독 결제(Payment, Toss)와는 별개 개념."""
from datetime import date, datetime, time
from uuid import UUID

from app.core.models import Claim, ClaimPayment, DailyQueue, Patient
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def create_payment(
    db: AsyncSession,
    hospital_id: UUID,
    claim_id: UUID,
    method: str,
    amount: int,
    processed_by_name: str,
) -> ClaimPayment:
    claim = await db.get(Claim, claim_id)
    if not claim or claim.hospital_id != hospital_id:
        raise HTTPException(status_code=404, detail="청구를 찾을 수 없습니다.")

    payment = ClaimPayment(
        hospital_id=hospital_id,
        claim_id=claim_id,
        method=method,
        amount=amount,
        processed_by_name=processed_by_name,
    )
    db.add(payment)

    # 이 청구에서 발생한 접수(DailyQueue)가 있으면 수납완료로 전환
    r_queue = await db.execute(
        select(DailyQueue).where(DailyQueue.claim_id == claim_id)
    )
    queue = r_queue.scalar_one_or_none()
    if queue:
        queue.status = "paid"

    await db.commit()
    await db.refresh(payment)
    return payment


async def list_payments(
    db: AsyncSession,
    hospital_id: UUID,
    start_date: date | None,
    end_date: date | None,
    method: str | None,
    page: int,
    size: int,
) -> tuple[int, list[tuple[ClaimPayment, Claim, Patient]]]:
    stmt = (
        select(ClaimPayment, Claim, Patient)
        .join(Claim, ClaimPayment.claim_id == Claim.id)
        .join(Patient, Claim.patient_id == Patient.id)
        .where(ClaimPayment.hospital_id == hospital_id)
    )
    stmt = _apply_filters(stmt, start_date, end_date, method)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = stmt.order_by(ClaimPayment.paid_at.desc()).offset((page - 1) * size).limit(size)
    rows = (await db.execute(stmt)).all()
    return total, rows


async def get_payment_summary(
    db: AsyncSession,
    hospital_id: UUID,
    start_date: date | None,
    end_date: date | None,
    method: str | None,
) -> dict:
    today = date.today()
    today_start = datetime.combine(today, time.min)
    today_end = datetime.combine(today, time.max)
    month_start = datetime.combine(today.replace(day=1), time.min)

    today_total = (await db.execute(
        select(func.coalesce(func.sum(ClaimPayment.amount), 0)).where(
            ClaimPayment.hospital_id == hospital_id,
            ClaimPayment.paid_at >= today_start,
            ClaimPayment.paid_at <= today_end,
        )
    )).scalar() or 0

    month_total = (await db.execute(
        select(func.coalesce(func.sum(ClaimPayment.amount), 0)).where(
            ClaimPayment.hospital_id == hospital_id,
            ClaimPayment.paid_at >= month_start,
        )
    )).scalar() or 0

    # 현금/카드 비율은 현재 필터(날짜 범위 + 수납방법)가 적용된 범위 내에서 집계
    filtered_stmt = select(ClaimPayment.method, func.sum(ClaimPayment.amount)).where(
        ClaimPayment.hospital_id == hospital_id
    )
    filtered_stmt = _apply_filters(filtered_stmt, start_date, end_date, method)
    filtered_stmt = filtered_stmt.group_by(ClaimPayment.method)
    rows = (await db.execute(filtered_stmt)).all()
    by_method = {m: amt or 0 for m, amt in rows}
    filtered_total = sum(by_method.values())
    cash_ratio = (by_method.get("cash", 0) / filtered_total * 100) if filtered_total else 0.0
    card_ratio = (by_method.get("card", 0) / filtered_total * 100) if filtered_total else 0.0

    return {
        "today_total": today_total,
        "month_total": month_total,
        "cash_ratio": round(cash_ratio, 1),
        "card_ratio": round(card_ratio, 1),
    }


def _apply_filters(stmt, start_date: date | None, end_date: date | None, method: str | None):
    if start_date:
        stmt = stmt.where(ClaimPayment.paid_at >= datetime.combine(start_date, time.min))
    if end_date:
        stmt = stmt.where(ClaimPayment.paid_at <= datetime.combine(end_date, time.max))
    if method:
        stmt = stmt.where(ClaimPayment.method == method)
    return stmt
