from uuid import UUID

from app.charting.service import get_medical_record
from app.core.audit import write_audit
from app.core.models import AcupuncturePoint, Doctor, MedicalRecordProcedure
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def add_procedure(
    db: AsyncSession,
    doctor: Doctor,
    record_id: UUID,
    data,
) -> MedicalRecordProcedure:
    # 권한 체크
    await get_medical_record(db, doctor, record_id)

    # 침술인 경우 금지 조합 검증
    if data.procedure_type == "침술" and data.details:
        points = data.details.get("points", [])
        if points:
            # 이미 저장된 침술 조회
            existing_result = await db.execute(
                select(MedicalRecordProcedure).where(
                    MedicalRecordProcedure.medical_record_id == record_id,
                    MedicalRecordProcedure.procedure_type == "침술",
                )
            )
            existing_procedures = existing_result.scalars().all()
            existing_points = []
            for ep in existing_procedures:
                if ep.details and "points" in ep.details:
                    existing_points.extend(ep.details["points"])

            # 금지 조합 체크
            for point_code in points:
                point_result = await db.execute(
                    select(AcupuncturePoint).where(
                        AcupuncturePoint.code == point_code
                    )
                )
                point = point_result.scalar_one_or_none()
                if point and point.forbidden_with:
                    conflicts = [
                        p for p in existing_points
                        if p in point.forbidden_with
                    ]
                    if conflicts:
                        raise HTTPException(
                            status_code=400,
                            detail=f"{point_code}는 {conflicts}와 동시 시술 불가합니다."
                        )

    procedure = MedicalRecordProcedure(
        medical_record_id=record_id,
        procedure_type=data.procedure_type,
        procedure_code=data.procedure_code,
        details=data.details,
        amount=data.amount,
    )
    db.add(procedure)
    await write_audit(
        db,
        table_name="medical_record_procedures",
        record_id=str(record_id),
        action="INSERT",
        actor_id=doctor.id,
        actor_type="doctor",
    )
    await db.commit()
    await db.refresh(procedure)
    return procedure


async def get_procedures(
    db: AsyncSession,
    doctor: Doctor,
    record_id: UUID,
) -> list[MedicalRecordProcedure]:
    await get_medical_record(db, doctor, record_id)

    result = await db.execute(
        select(MedicalRecordProcedure)
        .where(MedicalRecordProcedure.medical_record_id == record_id)
        .order_by(MedicalRecordProcedure.created_at.asc())
    )
    return list(result.scalars().all())


async def delete_procedure(
    db: AsyncSession,
    doctor: Doctor,
    procedure_id: UUID,
) -> None:
    result = await db.execute(
        select(MedicalRecordProcedure).where(
            MedicalRecordProcedure.id == procedure_id
        )
    )
    procedure = result.scalar_one_or_none()
    if not procedure:
        raise HTTPException(status_code=404, detail="시술을 찾을 수 없습니다.")

    # 권한 체크
    await get_medical_record(db, doctor, procedure.medical_record_id)

    await db.delete(procedure)
    await write_audit(
        db,
        table_name="medical_record_procedures",
        record_id=str(procedure_id),
        action="DELETE",
        actor_id=doctor.id,
        actor_type="doctor",
    )
    await db.commit()