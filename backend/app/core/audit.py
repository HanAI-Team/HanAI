import contextvars
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import AuditLog

# 개인정보 접속기록 요건(접속자 IP주소)을 write_audit() 호출부마다 일일이
# request를 넘기지 않고도 채우기 위한 요청 단위 컨텍스트. main.py의
# audit_ip_middleware가 요청마다 설정한다.
_request_ip: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "_request_ip", default=None
)


def set_request_ip(ip: str | None) -> None:
    _request_ip.set(ip)


def _now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


async def write_audit(
    db: AsyncSession,
    *,
    table_name: str,
    record_id: str,
    action: str,
    actor_id: UUID | None = None,
    actor_type: str | None = None,
    detail: str | None = None,
) -> None:
    log = AuditLog(
        table_name=table_name,
        record_id=record_id,
        action=action,
        actor_id=actor_id,
        actor_type=actor_type,
        changed_at=_now_str(),
        detail=detail,
        ip_address=_request_ip.get(),
    )
    db.add(log)
