import io
import uuid
from datetime import date, datetime, timezone
from uuid import UUID

import pandas as pd
from app.billing import service as billing_service
from app.billing.schema import (
    SpecialCaseRegistrationCreate,
    SpecialCaseRegistrationListResponse,
    SpecialCaseRegistrationResponse,
    SpecialCaseRegistrationUpdate,
)
from app.core.audit import write_audit
from app.core.database import get_db
from app.core.deps import get_current_doctor, get_current_user
from app.core.models import AIResult, DataDownloadLog, DataPurgeLog, Doctor, MedicalRecord, Patient, StaffAccount
from app.patients import service
from app.patients.schema import (
    DataPurgeLogListResponse,
    DataPurgeLogResponse,
    PatientCreate,
    PatientListResponse,
    PatientRecordListResponse,
    PatientResponse,
    PatientUpdate,
    RecentRecordSummary,
    RecordCreate,
)
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy import insert as sa_insert
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["patients"])


def _mask_rrn(rrn: str | None) -> str | None:
    """목록처럼 여러 명이 한 화면에 노출되는 곳에는 주민번호 원문 대신
    앞 6자리(생년월일)+성별코드 1자리만 보여주고 나머지는 마스킹한다."""
    digits = "".join(ch for ch in (rrn or "") if ch.isdigit())
    if len(digits) < 7:
        return None
    return f"{digits[:6]}-{digits[6]}******"


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
        .where(
            MedicalRecord.doctor_id == doctor.id,
            MedicalRecord.recorded_at.isnot(None),
        )
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
                    "patient_id": str(patient.id),
                    "record_id": str(rec.id),
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
    doctor: Doctor | StaffAccount = Depends(get_current_user),
    page: int = 1,
    size: int = 20,
    search: str | None = None,
):
    patients, total = await service.get_patients(db, doctor, page, size, search)
    if not patients:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="등록된 회원이 없습니다."
        )
    items = []
    for p in patients:
        item = PatientResponse.model_validate(p)
        item.rrn_masked = _mask_rrn(p.rrn)
        items.append(item)
    return PatientListResponse(
        total=total,
        page=page,
        size=size,
        items=items,
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

    existing = await _existing_patient_keys(db, doctor.hospital_id)
    rows_to_insert = []
    skipped = 0
    for row in df.to_dict("records"):
        name = str(row.get("cm_CustName", "")).strip()
        if not name:
            skipped += 1
            continue
        birth_date = _parse_yyyymmdd(row.get("cm_Birth")) or _birth_from_lifeno(
            row.get("cm_LifeNo")
        )
        if (name, birth_date) in existing:
            skipped += 1
            continue
        gender = _normalize_gender(row.get("cm_Sex"))
        phone = str(row.get("cm_HP") or row.get("cm_Tel") or "").strip() or None

        rows_to_insert.append({
            "id": uuid.uuid4(),
            "hospital_id": doctor.hospital_id,
            "name": name,
            "birth_date": birth_date,
            "gender": gender,
            "phone": phone,
        })
        existing.add((name, birth_date))

    if rows_to_insert:
        await db.execute(sa_insert(Patient), rows_to_insert)
        await db.commit()

    return {"inserted": len(rows_to_insert), "skipped": skipped}


async def _existing_patient_keys(db: AsyncSession, hospital_id) -> set[tuple]:
    result = await db.execute(
        select(Patient.name, Patient.birth_date).where(Patient.hospital_id == hospital_id)
    )
    return {(row.name, row.birth_date) for row in result}


@router.post("/import/excel")
async def import_excel(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    content = await file.read()
    filename = (file.filename or "").lower()
    try:
        engine = "openpyxl" if filename.endswith(".xlsx") else "xlrd"
        df = pd.read_excel(io.BytesIO(content), engine=engine, dtype=str, header=0)
    except Exception:
        raise HTTPException(status_code=400, detail="엑셀 파일을 읽을 수 없습니다.")

    df.columns = [str(c).strip() for c in df.columns]

    existing = await _existing_patient_keys(db, doctor.hospital_id)
    rows_to_insert = []
    skipped = 0
    for row in df.to_dict("records"):
        name = str(row.get("환자명", "")).strip()
        if not name or name.lower() == "nan":
            skipped += 1
            continue

        birth_date = _birth_from_lifeno(row.get("주민번호"))

        if (name, birth_date) in existing:
            skipped += 1
            continue

        gender_age = str(row.get("성별나이", "")).strip()
        if gender_age.startswith("여"):
            gender = "female"
        elif gender_age.startswith("남"):
            gender = "male"
        else:
            gender = None

        phone_raw = str(row.get("휴대전화", "") or "").strip()
        phone = phone_raw if phone_raw and phone_raw.lower() != "nan" else None

        address = str(row.get("주소", "") or "").strip()
        notes = str(row.get("비고", "") or "").strip()
        memo_parts = [p for p in [address, notes] if p and p.lower() != "nan"]
        memo = " | ".join(memo_parts) or None

        rows_to_insert.append({
            "id": uuid.uuid4(),
            "hospital_id": doctor.hospital_id,
            "name": name,
            "birth_date": birth_date,
            "gender": gender,
            "phone": phone,
            "memo": memo,
        })
        existing.add((name, birth_date))

    if rows_to_insert:
        await db.execute(sa_insert(Patient), rows_to_insert)
        await db.commit()

    return {"inserted": len(rows_to_insert), "skipped": skipped}


@router.get("/purge-logs", response_model=DataPurgeLogListResponse)
async def get_purge_logs(
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
    page: int = 1,
    size: int = 20,
):
    """개인정보 파기대장 조회. owner 전용, 자기 병원 것만 조회.

    ※ /{patient_id} 조회 라우트보다 먼저 등록해야 함 — 아래에 있으면 "purge-logs"가
    patient_id로 잘못 매칭됨.
    """
    if str(doctor.role) != "owner":
        raise HTTPException(status_code=403, detail="owner 계정만 접근 가능합니다.")

    total_result = await db.execute(
        select(func.count(DataPurgeLog.id)).where(DataPurgeLog.hospital_id == doctor.hospital_id)
    )
    total = total_result.scalar() or 0

    result = await db.execute(
        select(DataPurgeLog)
        .where(DataPurgeLog.hospital_id == doctor.hospital_id)
        .order_by(DataPurgeLog.purged_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    logs = result.scalars().all()

    return DataPurgeLogListResponse(
        total=total,
        page=page,
        size=size,
        items=[DataPurgeLogResponse.model_validate(log) for log in logs],
    )


@router.get("/purge-logs/csv")
async def export_purge_logs_csv(
    request: Request,
    reason: str = Query(..., min_length=1, max_length=500, description="다운로드 사유"),
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),
):
    """개인정보 파기대장 CSV 다운로드. owner 전용, 자기 병원 것만 조회.

    ※ /{patient_id} 조회 라우트보다 먼저 등록해야 함.
    """
    if str(doctor.role) != "owner":
        raise HTTPException(status_code=403, detail="owner 계정만 접근 가능합니다.")

    db.add(DataDownloadLog(
        id=uuid.uuid4(),
        hospital_id=doctor.hospital_id,
        doctor_id=doctor.id,
        download_type="purge_log",
        reason=reason,
        ip_address=request.client.host if request.client else None,
    ))
    await db.commit()

    result = await db.execute(
        select(DataPurgeLog)
        .where(DataPurgeLog.hospital_id == doctor.hospital_id)
        .order_by(DataPurgeLog.purged_at.desc())
    )
    logs = result.scalars().all()

    df = pd.DataFrame([{
        "환자명": log.patient_name_before or "",
        "사유": log.reason,
        "파기유형": log.purge_type,
        "파기일시": log.purged_at,
    } for log in logs])
    if df.empty:
        df = pd.DataFrame(columns=["환자명", "사유", "파기유형", "파기일시"])

    output = io.StringIO()
    df.to_csv(output, index=False, encoding="utf-8-sig")
    output.seek(0)

    return StreamingResponse(
        iter(["\ufeff" + output.getvalue()]),  # BOM: StringIO는 encoding= 인자를 무시하므로 직접 부착
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=purge_logs.csv"}
    )


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor | StaffAccount = Depends(get_current_user),
):
    patient = await service.get_patient(db, doctor, patient_id)
    await write_audit(
        db,
        table_name="patients",
        record_id=str(patient_id),
        action="READ",
        actor_id=doctor.id,
        actor_type="doctor",
    )
    await db.commit()
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


@router.patch("/{patient_id}", response_model=PatientResponse)
async def patch_patient(
    patient_id: UUID,
    data: PatientUpdate,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor | StaffAccount = Depends(get_current_user),
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
        medical_history=data.medical_history,
        selected_result=data.selected_result,
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
    from sqlalchemy import select

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
    await write_audit(
        db,
        table_name="medical_records",
        record_id=str(record_id),
        action="DELETE",
        actor_id=doctor.id,
        actor_type="doctor",
    )
    await db.delete(record)
    await db.commit()


@router.get("/{patient_id}/records")
async def get_patient_records(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor | StaffAccount = Depends(get_current_user),
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


@router.get("/{patient_id}/records/all", response_model=PatientRecordListResponse)
async def get_patient_records_all(
    patient_id: UUID,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    doctor: Doctor | StaffAccount = Depends(get_current_user),
):
    """환자 페이지에서 전체 진료 기록을 페이지 단위로 조회 (최근 5건 제한 없음)."""
    _, total, records = await service.get_patient_records_paginated(db, doctor, patient_id, page, size)
    return PatientRecordListResponse(
        total=total,
        page=page,
        size=size,
        items=[RecentRecordSummary.model_validate(r) for r in records],
    )


@router.get("/export/csv")
async def export_patients_csv(
    request: Request,
    reason: str = Query(..., min_length=1, max_length=500, description="다운로드 사유"),
    current_doctor: Doctor | StaffAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """환자 목록 CSV 다운로드 (헤딩 포함)"""
    db.add(DataDownloadLog(
        id=uuid.uuid4(),
        hospital_id=current_doctor.hospital_id,
        doctor_id=current_doctor.id,
        download_type="patient_list",
        reason=reason,
        ip_address=request.client.host if request.client else None,
    ))
    await db.commit()

    result = await db.execute(
        select(Patient)
        .where(Patient.hospital_id == current_doctor.hospital_id)
        .order_by(Patient.created_at.desc())
    )
    patients = result.scalars().all()

    df = pd.DataFrame([{
        "환자ID": str(p.id),
        "이름": p.name,
        "생년월일": str(p.birth_date) if p.birth_date else "",
        "성별": p.gender or "",
        "전화번호": p.phone or "",
        "보험종류": p.insurance_type or "",
        "메모": p.memo or "",
        "등록일": str(p.created_at),
    } for p in patients])
    if df.empty:
        df = pd.DataFrame(columns=["진료ID", "환자ID", "의사ID", "상태", "차트", "진료일시", "등록일"])
    output = io.StringIO()
    df.to_csv(output, index=False, encoding="utf-8-sig")  # utf-8-sig: 엑셀 한글 깨짐 방지
    output.seek(0)

    return StreamingResponse(
        iter(["\ufeff" + output.getvalue()]),  # BOM: StringIO는 encoding= 인자를 무시하므로 직접 부착
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=patients.csv"}
    )


@router.get("/export/records/csv")
async def export_records_csv(
    request: Request,
    reason: str = Query(..., min_length=1, max_length=500, description="다운로드 사유"),
    current_doctor: Doctor | StaffAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """진료 기록 CSV 다운로드 (헤딩 포함)"""
    db.add(DataDownloadLog(
        id=uuid.uuid4(),
        hospital_id=current_doctor.hospital_id,
        doctor_id=current_doctor.id,
        download_type="medical_records",
        reason=reason,
        ip_address=request.client.host if request.client else None,
    ))
    await db.commit()

    result = await db.execute(
        select(MedicalRecord)
        .where(MedicalRecord.hospital_id == current_doctor.hospital_id)
        .order_by(MedicalRecord.created_at.desc())
    )
    records = result.scalars().all()

    df = pd.DataFrame([{
        "진료ID": str(r.id),
        "환자ID": str(r.patient_id),
        "의사ID": str(r.doctor_id),
        "상태": r.status or "",
        "차트": r.chart_structured or "",
        "진료일시": str(r.recorded_at) if r.recorded_at else "",
        "등록일": str(r.created_at),
    } for r in records])

    output = io.StringIO()
    df.to_csv(output, index=False, encoding="utf-8-sig")
    output.seek(0)

    return StreamingResponse(
        iter(["\ufeff" + output.getvalue()]),  # BOM: StringIO는 encoding= 인자를 무시하므로 직접 부착
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=medical_records.csv"}
    )



@router.patch("/{patient_id}/anonymize", response_model=PatientResponse)
async def anonymize_patient(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor = Depends(get_current_doctor),  # owner만 가능
):
    if str(doctor.role) != "owner":
        raise HTTPException(status_code=403, detail="owner 계정만 접근 가능합니다.")
    return await service.anonymize_patient(db, doctor, patient_id)


@router.post(
    "/{patient_id}/special-case-registrations",
    response_model=SpecialCaseRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_special_case_registration(
    patient_id: UUID,
    data: SpecialCaseRegistrationCreate,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor | StaffAccount = Depends(get_current_user),
):
    return await billing_service.create_special_case_registration(db, doctor, patient_id, data)


@router.get(
    "/{patient_id}/special-case-registrations",
    response_model=SpecialCaseRegistrationListResponse,
)
async def get_special_case_registrations(
    patient_id: UUID,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor | StaffAccount = Depends(get_current_user),
):
    registrations = await billing_service.get_special_case_registrations(db, doctor, patient_id)
    return SpecialCaseRegistrationListResponse(
        items=[SpecialCaseRegistrationResponse.model_validate(r) for r in registrations]
    )


@router.patch(
    "/{patient_id}/special-case-registrations/{registration_id}",
    response_model=SpecialCaseRegistrationResponse,
)
async def update_special_case_registration(
    patient_id: UUID,
    registration_id: UUID,
    data: SpecialCaseRegistrationUpdate,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor | StaffAccount = Depends(get_current_user),
):
    return await billing_service.update_special_case_registration(
        db, doctor, patient_id, registration_id, data
    )


@router.post(
    "/{patient_id}/special-case-registrations/{registration_id}/deactivate",
    response_model=SpecialCaseRegistrationResponse,
)
async def deactivate_special_case_registration(
    patient_id: UUID,
    registration_id: UUID,
    db: AsyncSession = Depends(get_db),
    doctor: Doctor | StaffAccount = Depends(get_current_user),
):
    return await billing_service.deactivate_special_case_registration(
        db, doctor, patient_id, registration_id
    )