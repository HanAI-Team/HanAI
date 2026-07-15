"""보관기간 초과 로그 자동 삭제.

보관기간 기준:
- login_logs: 1년 (개인정보보호법)
- audit_logs: 5년 (의료법)
- account_histories: 5년 (의료법)
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.core.database import AsyncSessionLocal
from sqlalchemy import text

logger = logging.getLogger(__name__)

RETENTION = {
    "login_logs": timedelta(days=365 * 2),
    "audit_logs": timedelta(days=365 * 5),
    "account_histories": timedelta(days=365 * 5),
}

_CLEANUP_INTERVAL_SECONDS = 24 * 60 * 60  # 24시간


_TABLE_CONFIG = {
    # table: (timestamp_column, is_string_yyyymmddhhmmss)
    "login_logs":       ("attempted_at", False),
    "audit_logs":       ("changed_at",   True),   # String "YYYYMMDDHHMMSS"
    "account_histories": ("started_at",   False),
}


async def purge_old_logs() -> None:
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        for table, delta in RETENTION.items():
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


async def run_cleanup_loop() -> None:
    while True:
        try:
            await purge_old_logs()
        except Exception:
            logger.exception("로그 정리 중 오류 발생")
        await asyncio.sleep(_CLEANUP_INTERVAL_SECONDS)
