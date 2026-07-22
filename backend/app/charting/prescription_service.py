from decimal import Decimal
from uuid import UUID

from app.billing.calculator import (
    calculate_prescription_price,
    validate_prescription_limits,
)
from app.charting.service import get_medical_record
from app.core.audit import write_audit
from app.core.models import Doctor, Prescription
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession


async def add_prescription(
    db: AsyncSession,
    doctor: Doctor,
    record_id: UUID,
    data,
) -> Prescription:
    # 권한 체크 (내 병원 진료인지)
    await get_medical_record(db, doctor, record_id)

    # 금액 자동 계산 (총투약일수 반영된 전체 처방 금액 — 실제 청구/표시용)
    total_dosage_price = 0
    if data.unit_price and data.total_dosage_days:
        total_dosage_price = calculate_prescription_price(
            unit_price=data.unit_price,
            daily_dosage_ratio=data.daily_dosage_ratio,
            total_dosage_days=data.total_dosage_days,
            birth_date=data.patient_birth_date,
        )

    # 한도 검증 — 가미제/임의처방 인정기준(종수·중량·투약비)은 모두 "1일" 기준이므로,
    # 총투약일수가 곱해진 total_dosage_price가 아니라 1일치 금액으로 비교해야 한다.
    # (총액으로 비교하면 1일당 금액은 정상인데 여러 날 처방했다는 이유만으로
    #  부당하게 한도 초과로 걸리게 됨)
    if data.prescription_type in ("가감처방", "가미제", "임의처방"):
        daily_price = 0
        if data.unit_price:
            daily_price = calculate_prescription_price(
                unit_price=data.unit_price,
                daily_dosage_ratio=data.daily_dosage_ratio,
                total_dosage_days=1,
                birth_date=data.patient_birth_date,
            )
        violations = validate_prescription_limits(
            prescription_type=data.prescription_type,
            species_count=data.species_count or 0,
            total_weight_g=Decimal(str(data.total_weight_g or 0)),
            total_dosage_price=daily_price,
            birth_date=data.patient_birth_date,
        )
        if violations:
            raise HTTPException(status_code=400, detail=violations)

    prescription = Prescription(
        medical_record_id=record_id,
        prescription_name=data.prescription_name,
        ingredients=data.ingredients,
        dosage=data.dosage,
        notes=data.notes,
        prescription_type=data.prescription_type,
        adjustment_type=data.adjustment_type,
        formula_code=data.formula_code,
        unit_price=data.unit_price,
        daily_dosage_ratio=data.daily_dosage_ratio,
        total_dosage_days=data.total_dosage_days,
        total_dosage_price=total_dosage_price,
        species_count=data.species_count,
        total_weight_g=data.total_weight_g,
        low_cost_substitute=data.low_cost_substitute,
        low_cost_surcharge=data.low_cost_surcharge,
        dispensing_fee=data.dispensing_fee,
    )
    db.add(prescription)
    await write_audit(
        db,
        table_name="prescriptions",
        record_id=str(record_id),
        action="INSERT",
        actor_id=doctor.id,
        actor_type="doctor",
    )
    await db.commit()
    await db.refresh(prescription)
    return prescription


async def get_prescriptions(
    db: AsyncSession,
    doctor: Doctor,
    record_id: UUID,
) -> list[Prescription]:
    from sqlalchemy import select

    await get_medical_record(db, doctor, record_id)

    result = await db.execute(
        select(Prescription)
        .where(Prescription.medical_record_id == record_id)
        .order_by(Prescription.created_at.asc())
    )
    return list(result.scalars().all())


async def delete_prescription(
    db: AsyncSession,
    doctor: Doctor,
    prescription_id: UUID,
) -> None:
    from sqlalchemy import select

    result = await db.execute(
        select(Prescription).where(Prescription.id == prescription_id)
    )
    prescription = result.scalar_one_or_none()
    if not prescription:
        raise HTTPException(status_code=404, detail="처방을 찾을 수 없습니다.")

    # 권한 체크
    await get_medical_record(db, doctor, prescription.medical_record_id)

    await db.delete(prescription)
    await write_audit(
        db,
        table_name="prescriptions",
        record_id=str(prescription_id),
        action="DELETE",
        actor_id=doctor.id,
        actor_type="doctor",
    )
    await db.commit()