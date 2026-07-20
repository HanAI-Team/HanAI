import json
import logging
import uuid
from datetime import date, datetime, timezone
from uuid import UUID

from app.charting import prescription_service, procedure_service, service
from app.charting.schema import (
    ChangeLogItem,
    ChangeLogListResponse,
    FinalizeRecordRequest,
    MedicalRecordResponse,
    PrescriptionCreateRequest,
    PrescriptionResponse,
    ProcedureCreateRequest,
    ProcedureResponse,
    UpdateAudioUrlRequest,
    UpdateKcdCodeRequest,
    UpdateMedicalHistoryRequest,
    UpdateStatusRequest,
)
from app.core.audit import write_audit
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.models import Doctor, MedicalRecord, Patient, StaffAccount
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["charting"])

logger = logging.getLogger(__name__)


async def _stream_chart(**kwargs):
    try:
        async for event in service.process_chart_stream(**kwargs):
            yield json.dumps(event, ensure_ascii=False) + "\n"
    except HTTPException as e:
        yield json.dumps({"type": "error", "detail": e.detail}, ensure_ascii=False) + "\n"
    except Exception:
        logger.exception("[charting] 분석 스트리밍 중 오류")
        yield json.dumps(
            {"type": "error", "detail": "분석 중 오류가 발생했습니다."},
            ensure_ascii=False,
        ) + "\n"


@router.post("/")
async def chart(
    patient_id: uuid.UUID = Form(...),
    audios: list[UploadFile] = File(...),
    symptom_text: str | None = Form(None),
    medical_history: str | None = Form(None),
    current_doctor: Doctor | StaffAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return StreamingResponse(
        _stream_chart(
            audio_files=audios,
            patient_id=patient_id,
            doctor_id=UUID(str(current_doctor.id)),
            hospital_id=UUID(str(current_doctor.hospital_id)),
            db=db,
            symptom_text=symptom_text,
            medical_history=medical_history,
        ),
        media_type="application/x-ndjson",
    )


@router.get("/patient/{patient_id}", response_model=list[MedicalRecordResponse])
async def get_patient_records(
    patient_id: uuid.UUID,
    current_doctor: Doctor | StaffAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_records_by_patient(db, patient_id, current_doctor)


@router.get("/change-log", response_model=ChangeLogListResponse)
async def get_change_log(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    date_from: date | None = Query(None, description="조회 시작일 (최초입력일 created_at 기준)"),
    date_to: date | None = Query(None, description="조회 종료일 (최초입력일 created_at 기준)"),
    current_doctor: Doctor | StaffAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """진료기록 최초입력일자/최종수정일자 조회 (HIRA 변경일 관리)."""
    stmt = (
        select(MedicalRecord, Patient.name)
        .join(Patient, Patient.id == MedicalRecord.patient_id)
        .where(MedicalRecord.hospital_id == current_doctor.hospital_id)
    )
    if date_from:
        stmt = stmt.where(
            MedicalRecord.created_at >= datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc)
        )
    if date_to:
        stmt = stmt.where(
            MedicalRecord.created_at <= datetime.combine(date_to, datetime.max.time(), tzinfo=timezone.utc)
        )

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = stmt.order_by(MedicalRecord.created_at.desc()).offset((page - 1) * size).limit(size)
    rows = (await db.execute(stmt)).all()
    items = [
        ChangeLogItem(
            id=record.id,
            patient_id=record.patient_id,
            patient_name=patient_name,
            doctor_id=record.doctor_id,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
        for record, patient_name in rows
    ]
    return ChangeLogListResponse(total=total, page=page, size=size, items=items)


@router.get("/{record_id}", response_model=MedicalRecordResponse)
async def get_record(
    record_id: uuid.UUID,
    doctor: Doctor | StaffAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    record =  await service.get_medical_record(db, doctor, record_id)
    await write_audit(
        db,
        table_name="medical_records",
        record_id=str(record_id),
        action="READ",
        actor_id=doctor.id,
        actor_type="doctor",
    )
    await db.commit()
    return record



@router.patch("/{record_id}/status", response_model=MedicalRecordResponse)
async def update_status(
    record_id: uuid.UUID,
    data: UpdateStatusRequest,
    current_doctor: Doctor | StaffAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.update_record_status(db, current_doctor, record_id, data.status)


@router.patch("/{record_id}/audio", response_model=MedicalRecordResponse)
async def update_audio(
    record_id: uuid.UUID,
    data: UpdateAudioUrlRequest,
    current_doctor: Doctor | StaffAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.update_audio_url(db, current_doctor, record_id, data.audio_file_url)


@router.patch("/{record_id}/medical-history", response_model=MedicalRecordResponse)
async def update_medical_history(
    record_id: uuid.UUID,
    data: UpdateMedicalHistoryRequest,
    current_doctor: Doctor | StaffAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.update_medical_history(
        db, current_doctor, record_id, data.medical_history
    )


@router.patch("/{record_id}/kcd-code", response_model=MedicalRecordResponse)
async def update_kcd_code(
    record_id: uuid.UUID,
    data: UpdateKcdCodeRequest,
    current_doctor: Doctor | StaffAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.update_kcd_code(db, current_doctor, record_id, data.kcd_code)


@router.patch("/{record_id}/finalize", response_model=MedicalRecordResponse)
async def finalize_record(
    record_id: uuid.UUID,
    data: FinalizeRecordRequest,
    current_doctor: Doctor | StaffAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.finalize_record(
        db, current_doctor, record_id, data.chart_structured, data.selected_result
    )



@router.post("/{record_id}/prescriptions", response_model=PrescriptionResponse)
async def add_prescription(
    record_id: uuid.UUID,
    data: PrescriptionCreateRequest,
    current_doctor: Doctor | StaffAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await prescription_service.add_prescription(db, current_doctor, record_id, data)


@router.get("/{record_id}/prescriptions", response_model=list[PrescriptionResponse])
async def get_prescriptions(
    record_id: uuid.UUID,
    current_doctor: Doctor | StaffAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await prescription_service.get_prescriptions(db, current_doctor, record_id)


@router.delete("/prescriptions/{prescription_id}", status_code=204)
async def delete_prescription(
    prescription_id: uuid.UUID,
    current_doctor: Doctor | StaffAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await prescription_service.delete_prescription(db, current_doctor, prescription_id)


@router.post("/{record_id}/procedures", response_model=ProcedureResponse)
async def add_procedure(
    record_id: uuid.UUID,
    data: ProcedureCreateRequest,
    current_doctor: Doctor | StaffAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await procedure_service.add_procedure(db, current_doctor, record_id, data)


@router.get("/{record_id}/procedures", response_model=list[ProcedureResponse])
async def get_procedures(
    record_id: uuid.UUID,
    current_doctor: Doctor | StaffAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await procedure_service.get_procedures(db, current_doctor, record_id)


@router.delete("/procedures/{procedure_id}", status_code=204)
async def delete_procedure(
    procedure_id: uuid.UUID,
    current_doctor: Doctor | StaffAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await procedure_service.delete_procedure(db, current_doctor, procedure_id)