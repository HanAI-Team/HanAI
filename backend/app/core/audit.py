from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import AuditLog


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
    )
    db.add(log)
