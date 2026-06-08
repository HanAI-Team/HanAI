import io
from datetime import date, datetime, timezone

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.core.database import get_db
from app.core.deps import get_current_doctor
from app.core.models import Doctor, MedicalRecord, Patient
from app.patients import service
from app.core.models import AIResult
from app.patients.schema import (
    PatientCreate,
    PatientUpdate,
    PatientListResponse,
    PatientResponse,
    RecentRecordSummary,
    RecordCreate,
)

router = APIRouter(tags=["patients"])


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    total_patients_result = await db.execute(
        select(func.count(Patient.id)).where(Patient.hospital_id == doctor.hospital_id)
    )
    total_patients = total_patients_result.scalar() or 0

    today_records_result = await db.execute(
        select(func.count(MedicalRecord.id)).where(
            MedicalRecord.doctor_id == doctor.id,
            MedicalRecord.recorded_at >= today_start,
        )
    )
    today_records = today_records_result.scalar() or 0

    recent_result = await db.execute(
        select(MedicalRecord)
        .where(MedicalRecord.doctor_id == doctor.id)
        .order_by(MedicalRecord.recorded_at.desc())
        .limit(5)
    )
    recent_records = recent_result.scalars().all()

    recent = []
    for rec in recent_records:
        patient_result = await db.execute(
            select(Patient).where(Patient.id == rec.patient_id)
        )
        patient = patient_result.scalar_one_or_none()
        if patient:
            recent.append(
                {
                    "patient_name": patient.name,
                    "recorded_at": rec.recorded_at,
                    "chart_structured": rec.chart_structured,
                }
            )

    return {
        "total_patients": total_patients,
        "today_records": today_records,
        "recent_records": recent,
    }


@router.get("/", response_model=PatientListResponse)
async def get_patients(
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
    page: int = 1,
    size: int = 20,
    search: str | None = None,
):
    patients, total = await service.get_patients(db, doctor, page, size, search)
    if not patients:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="등록된 회원이 없습니다."
        )
    return PatientListResponse(
        total=total,
        page=page,
        size=size,
        items=[PatientResponse.model_validate(p) for p in patients],
    )


def _parse_yyyymmdd(value) -> date | None:
    s = str(value or "").strip().replace("-", "")
    if len(s) >= 8:
        try:
            return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
        except Exception:
            pass
    return None


def _birth_from_lifeno(life_no) -> date | None:
    s = str(life_no or "").strip().replace("-", "")
    if len(s) < 7:
        return None
    try:
        yy, mm, dd = int(s[0:2]), int(s[2:4]), int(s[4:6])
        century_digit = int(s[6])
        yyyy = 2000 + yy if century_digit in (3, 4) else 1900 + yy
        return date(yyyy, mm, dd)
    except Exception:
        return None


def _normalize_gender(value) -> str | None:
    v = str(value or "").strip().upper()
    if v in ("M", "1", "남"):
        return "male"
    if v in ("F", "2", "여"):
        return "female"
    return None


@router.post("/import/csv")
async def import_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    content = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig", dtype=str)
    except Exception:
        raise HTTPException(status_code=400, detail="CSV 파일을 읽을 수 없습니다.")

    inserted = skipped = 0
    for _, row in df.iterrows():
        name = str(row.get("cm_CustName", "")).strip()
        if not name:
            skipped += 1
            continue
        birth_date = _parse_yyyymmdd(row.get("cm_Birth")) or _birth_from_lifeno(
            row.get("cm_LifeNo")
        )
        gender = _normalize_gender(row.get("cm_Sex"))
        phone = str(row.get("cm_HP") or row.get("cm_Tel") or "").strip() or None

        try:
            await service.create_patient(
                db,
                doctor,
                PatientCreate(
                    name=name,
                    birth_date=birth_date,
                    gender=gender,
                    phone=phone,
                ),
            )
            inserted += 1
        except Exception:
            skipped += 1

    return {"inserted": inserted, "skipped": skipped}


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    patient = await service.get_patient(db, doctor, patient_id)

    return patient


@router.post(
    "/register", response_model=PatientResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    data: PatientCreate,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):

    patient = await service.create_patient(db, doctor, data)
    return patient


@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: UUID,
    data: PatientUpdate,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    patient = await service.update_patient(db, doctor, patient_id, data)

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="등록되지 않은 회원입니다."
        )
    return patient


@router.post("/{patient_id}/records", status_code=201)
async def create_record(
    patient_id: UUID,
    data: RecordCreate,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    from datetime import datetime, timezone
    from app.core.models import MedicalRecord

    patient = await service.get_patient(db, doctor, patient_id)
    record = MedicalRecord(
        patient_id=patient.id,
        doctor_id=doctor.id,
        hospital_id=doctor.hospital_id,
        chart_structured=data.chart_structured,
        raw_transcription=data.raw_transcription,
        status="completed",
        recorded_at=datetime.now(timezone.utc),
    )
    db.add(record)
    await db.flush()

    if data.chart_structured:

        ai_result = AIResult(
            medical_record_id=record.id,
            diagnosis_suggestion=data.chart_structured,
        )
        db.add(ai_result)

    await db.commit()
    await db.refresh(record)
    return {"id": str(record.id)}


@router.delete("/{patient_id}/records/{record_id}", status_code=204)
async def delete_record(
    patient_id: UUID,
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    from app.core.models import MedicalRecord
    from sqlalchemy import select, delete

    await service.get_patient(db, doctor, patient_id)
    result = await db.execute(
        select(MedicalRecord).where(
            MedicalRecord.id == record_id,
            MedicalRecord.patient_id == patient_id,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="진료 이력을 찾을 수 없습니다.",
        )
    await db.delete(record)
    await db.commit()


@router.get("/{patient_id}/records")
async def get_patient_records(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    patient, records = await service.get_patient_with_records(db, doctor, patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="등록되지 않은 회원입니다."
        )
    return {
        "patient": PatientResponse.model_validate(patient),
        "records": [RecentRecordSummary.model_validate(r) for r in records],
    }
