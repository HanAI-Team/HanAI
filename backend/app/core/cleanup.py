"""보관기간 초과 로그 / 의료 데이터 자동 삭제.

보관기간 기준:
- login_logs: 1년 (개인정보보호법)
- audit_logs: 5년 (의료법)
- account_histories: 5년 (의료법)
- access_control_logs: 3년 (HIRA 청구SW 기능검사 보안 기준)
- medical_records: 10년 (의료법)
- claims: 5년 (건보법 명세서 기준)
- prescriptions: 3년 (건보법 처방전 기준)
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.core.database import AsyncSessionLocal
from app.core.models import DataPurgeLog
from sqlalchemy import bindparam, text

logger = logging.getLogger(__name__)

RETENTION = {
    "login_logs": timedelta(days=365 * 2),
    "audit_logs": timedelta(days=365 * 5),
    "account_histories": timedelta(days=365 * 5),
    "access_control_logs": timedelta(days=365 * 3),
    "medical_records": timedelta(days=365 * 10),
    "claims": timedelta(days=365 * 5),
    "prescriptions": timedelta(days=365 * 3),
}

_CLEANUP_INTERVAL_SECONDS = 24 * 60 * 60  # 24시간


_TABLE_CONFIG = {
    # table: (timestamp_column, is_string_yyyymmddhhmmss)
    "login_logs":       ("attempted_at", False),
    "audit_logs":       ("changed_at",   True),   # String "YYYYMMDDHHMMSS"
    "account_histories": ("started_at",   False),
    "access_control_logs": ("acted_at",  True),   # String "YYYYMMDDHHMMSS"
}


async def purge_old_logs() -> None:
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        for table in _TABLE_CONFIG:
            delta = RETENTION[table]
            cutoff = now - delta
            col, is_str = _TABLE_CONFIG[table]
            if is_str:
                cutoff_val = cutoff.strftime("%Y%m%d%H%M%S")
                result = await db.execute(
                    text(f"DELETE FROM {table} WHERE {col} < :cutoff"),
                    {"cutoff": cutoff_val},
                )
            else:
                result = await db.execute(
                    text(f"DELETE FROM {table} WHERE {col} < :cutoff"),
                    {"cutoff": cutoff},
                )
            deleted = result.rowcount
            if deleted:
                logger.info("cleanup: %s에서 %d건 삭제 (기준: %s)", table, deleted, cutoff.date())
        await db.commit()


async def _purge_prescriptions(db, now: datetime) -> None:
    cutoff = now - RETENTION["prescriptions"]
    result = await db.execute(
        text(
            "SELECT p.id, mr.hospital_id, mr.doctor_id, mr.patient_id "
            "FROM prescriptions p JOIN medical_records mr ON mr.id = p.medical_record_id "
            "WHERE p.created_at < :cutoff"
        ),
        {"cutoff": cutoff},
    )
    rows = result.all()
    if not rows:
        return
    ids = [row.id for row in rows]
    purged_at = now.strftime("%Y%m%d%H%M%S")

    for row in rows:
        logger.warning(
            "cleanup: prescriptions id=%s 보관기간(3년) 경과로 파기 (hospital_id=%s)",
            row.id, row.hospital_id,
        )
        db.add(DataPurgeLog(
            hospital_id=row.hospital_id,
            doctor_id=row.doctor_id,
            patient_id=row.patient_id,
            reason="건보법상 처방전 보관기간(3년) 경과 자동 파기",
            purge_type="delete",
            purged_at=purged_at,
        ))

    await db.execute(
        text("DELETE FROM prescriptions WHERE id IN :ids").bindparams(bindparam("ids", expanding=True)),
        {"ids": ids},
    )
    logger.info("cleanup: prescriptions에서 %d건 삭제 (기준: %s)", len(ids), cutoff.date())


async def _purge_medical_records(db, now: datetime) -> None:
    cutoff = now - RETENTION["medical_records"]
    result = await db.execute(
        text("SELECT id, hospital_id, doctor_id, patient_id FROM medical_records WHERE created_at < :cutoff"),
        {"cutoff": cutoff},
    )
    rows = result.all()
    if not rows:
        return
    ids = [row.id for row in rows]
    purged_at = now.strftime("%Y%m%d%H%M%S")

    # ai_results/claim_line_items/prescriptions는 medical_records를 NOT NULL로 참조하며
    # DB에 ondelete 설정이 없어 먼저 지우지 않으면 FK 위반이 난다.
    # medical_record_procedures는 ondelete="CASCADE"가 걸려 있어 별도 삭제가 필요 없다.
    for child_table, col in (
        ("ai_results", "medical_record_id"),
        ("claim_line_items", "medical_record_id"),
        ("prescriptions", "medical_record_id"),
    ):
        await db.execute(
            text(f"DELETE FROM {child_table} WHERE {col} IN :ids").bindparams(bindparam("ids", expanding=True)),
            {"ids": ids},
        )

    for row in rows:
        logger.warning(
            "cleanup: medical_records id=%s 보관기간(10년) 경과로 파기 (hospital_id=%s, doctor_id=%s)",
            row.id, row.hospital_id, row.doctor_id,
        )
        db.add(DataPurgeLog(
            hospital_id=row.hospital_id,
            doctor_id=row.doctor_id,
            patient_id=row.patient_id,
            reason="의료법상 진료기록 보관기간(10년) 경과 자동 파기",
            purge_type="delete",
            purged_at=purged_at,
        ))

    await db.execute(
        text("DELETE FROM medical_records WHERE id IN :ids").bindparams(bindparam("ids", expanding=True)),
        {"ids": ids},
    )
    logger.info("cleanup: medical_records에서 %d건 삭제 (기준: %s)", len(ids), cutoff.date())


async def _purge_claims(db, now: datetime) -> None:
    cutoff = now - RETENTION["claims"]
    result = await db.execute(
        text("SELECT id, hospital_id, doctor_id, patient_id FROM claims WHERE created_at < :cutoff"),
        {"cutoff": cutoff},
    )
    rows = result.all()
    if not rows:
        return
    ids = [row.id for row in rows]
    purged_at = now.strftime("%Y%m%d%H%M%S")

    # medical_records는 의료법상 10년 보관 대상이라 claim 만료(5년)만으로 함께 지울 수 없으므로
    # 삭제 대신 연결만 끊는다. claim_line_items/claim_resubmission_histories는 claim에 종속된
    # 청구 서류이므로 claim과 함께 파기한다.
    await db.execute(
        text("UPDATE medical_records SET claim_id = NULL WHERE claim_id IN :ids").bindparams(bindparam("ids", expanding=True)),
        {"ids": ids},
    )
    for child_table in ("claim_line_items", "claim_resubmission_histories"):
        await db.execute(
            text(f"DELETE FROM {child_table} WHERE claim_id IN :ids").bindparams(bindparam("ids", expanding=True)),
            {"ids": ids},
        )

    for row in rows:
        logger.warning(
            "cleanup: claims id=%s 보관기간(5년) 경과로 파기 (hospital_id=%s, doctor_id=%s)",
            row.id, row.hospital_id, row.doctor_id,
        )
        db.add(DataPurgeLog(
            hospital_id=row.hospital_id,
            doctor_id=row.doctor_id,
            patient_id=row.patient_id,
            reason="건보법상 청구명세서 보관기간(5년) 경과 자동 파기",
            purge_type="delete",
            purged_at=purged_at,
        ))

    await db.execute(
        text("DELETE FROM claims WHERE id IN :ids").bindparams(bindparam("ids", expanding=True)),
        {"ids": ids},
    )
    logger.info("cleanup: claims에서 %d건 삭제 (기준: %s)", len(ids), cutoff.date())


async def purge_old_medical_data() -> None:
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        await _purge_prescriptions(db, now)
        await _purge_medical_records(db, now)
        await _purge_claims(db, now)
        await db.commit()


async def run_cleanup_loop() -> None:
    while True:
        try:
            await purge_old_logs()
        except Exception:
            logger.exception("로그 정리 중 오류 발생")
        try:
            await purge_old_medical_data()
        except Exception:
            logger.exception("의료 데이터 정리 중 오류 발생")
        await asyncio.sleep(_CLEANUP_INTERVAL_SECONDS)
