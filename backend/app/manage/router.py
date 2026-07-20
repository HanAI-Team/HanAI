import io
import uuid
from typing import Literal

from app.core.csv_export import csv_response
from app.core.database import get_db
from app.core.deps import get_current_doctor
from app.core.models import (
    AccessControlLog,
    AccountHistory,
    AuditLog,
    Claim,
    ClaimLineItem,
    ClaimRejectionCode,
    DailyQueue,
    DataDownloadLog,
    Doctor,
    DrugMaster,
    FeeMaster,
    LoginLog,
    MedicalRecord,
    Patient,
    Prescription,
    StaffAccount,
)
from app.core.timezone import today_kst
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["manage"])

# HIRA 청구SW 기능검사 "전체 DB 내역 추출" 시연용 화이트리스트.
TABLE_WHITELIST: dict[str, type] = {
    "patients": Patient,
    "medical_records": MedicalRecord,
    "claims": Claim,
    "claim_line_items": ClaimLineItem,
    "prescriptions": Prescription,
    "fee_master": FeeMaster,
    "drug_master": DrugMaster,
    "claim_rejection_codes": ClaimRejectionCode,
    "audit_logs": AuditLog,
    "login_logs": LoginLog,
    "account_histories": AccountHistory,
    "access_control_logs": AccessControlLog,
    "daily_queue": DailyQueue,
}

# hospital_id 컬럼을 직접 가진 테이블
_DIRECT_HOSPITAL_TABLES = {"patients", "medical_records", "claims", "daily_queue", "access_control_logs"}
# hospital_id가 없어 전국 공통(마스터 데이터)으로 취급 — 필터 없이 전체 반환
_GLOBAL_TABLES = {"fee_master", "drug_master", "claim_rejection_codes"}
# actor/account id로 소속 병원의 의사·직원인지 판별해야 하는 로그성 테이블
_ACTOR_SCOPED_TABLES = {"audit_logs": AuditLog.actor_id, "login_logs": LoginLog.account_id, "account_histories": AccountHistory.account_id}


def _stringify(value) -> str:
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _row_to_dict(table_name: str, model: type, row) -> dict[str, str]:
    result: dict[str, str] = {}
    for col in model.__table__.columns:
        raw = getattr(row, col.name)
        if table_name == "patients" and col.name == "rrn":
            result[col.name] = "***-*******" if raw else ""
        else:
            result[col.name] = _stringify(raw)
    return result


async def _fetch_rows(db: AsyncSession, table_name: str, model: type, hospital_id) -> list:
    if table_name in _GLOBAL_TABLES:
        stmt = select(model)
    elif table_name == "claim_line_items":
        stmt = (
            select(ClaimLineItem)
            .join(Claim, Claim.id == ClaimLineItem.claim_id)
            .where(Claim.hospital_id == hospital_id)
        )
    elif table_name == "prescriptions":
        stmt = (
            select(Prescription)
            .join(MedicalRecord, MedicalRecord.id == Prescription.medical_record_id)
            .where(MedicalRecord.hospital_id == hospital_id)
        )
    elif table_name in _ACTOR_SCOPED_TABLES:
        doctor_ids = (await db.execute(select(Doctor.id).where(Doctor.hospital_id == hospital_id))).scalars().all()
        staff_ids = (await db.execute(select(StaffAccount.id).where(StaffAccount.hospital_id == hospital_id))).scalars().all()
        all_ids = list(doctor_ids) + list(staff_ids)
        id_column = _ACTOR_SCOPED_TABLES[table_name]
        stmt = select(model).where(id_column.in_(all_ids))
    elif table_name in _DIRECT_HOSPITAL_TABLES:
        stmt = select(model).where(model.hospital_id == hospital_id)
    else:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 테이블입니다: {table_name}")

    result = await db.execute(stmt)
    return result.scalars().all()


def _xlsx_response(filename_base: str, columns: list[str], rows: list[dict[str, str]]) -> StreamingResponse:
    wb = Workbook()
    ws = wb.active
    ws.append(columns)
    for row in rows:
        ws.append([row[c] for c in columns])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename_base}.xlsx"},
    )


@router.get("/db-export")
async def export_db_table(
    request: Request,
    table: str = Query(..., description="추출할 테이블명 (화이트리스트)"),
    format: Literal["csv", "xlsx"] = Query("csv"),
    reason: str = Query(..., min_length=1, max_length=500, description="다운로드 사유"),
    current_doctor: Doctor = Depends(get_current_doctor),
    db: AsyncSession = Depends(get_db),
):
    """HIRA 청구SW 기능검사용 — DB 테이블 전체 내역을 TEXT(CSV)/Excel로 추출."""
    if current_doctor.role != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="오너 계정만 접근 가능합니다.")

    model = TABLE_WHITELIST.get(table)
    if model is None:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 테이블입니다: {table}")

    rows = await _fetch_rows(db, table, model, current_doctor.hospital_id)
    columns = [c.name for c in model.__table__.columns]
    data_rows = [_row_to_dict(table, model, r) for r in rows]

    db.add(DataDownloadLog(
        id=uuid.uuid4(),
        hospital_id=current_doctor.hospital_id,
        doctor_id=current_doctor.id,
        download_type=f"db_export:{table}",
        reason=reason,
        ip_address=request.client.host if request.client else None,
    ))
    await db.commit()

    filename_base = f"{table}_{today_kst().strftime('%Y%m%d')}"
    if format == "xlsx":
        return _xlsx_response(filename_base, columns, data_rows)
    return csv_response(f"{filename_base}.csv", columns, [[row[c] for c in columns] for row in data_rows])
