from datetime import date, datetime
from uuid import UUID

from app.core.models import DailyQueue
from pydantic import BaseModel


class QueueResponse(BaseModel):
    id: UUID
    patient_id: UUID
    patient_name: str = ""
    doctor_id: UUID | None
    queue_date: date
    checked_in_at: datetime
    status: str
    source: str
    assigned_bed: str | None = None
    claim_id: UUID | None = None

    @classmethod
    def from_orm_with_patient(cls, queue: "DailyQueue") -> "QueueResponse":
        return cls(
            id=queue.id,
            patient_id=queue.patient_id,
            patient_name=queue.patient.name if queue.patient else "",
            doctor_id=queue.doctor_id,
            queue_date=queue.queue_date,
            checked_in_at=queue.checked_in_at,
            status=queue.status,
            source=queue.source,
            assigned_bed=queue.assigned_bed,
            claim_id=queue.claim_id,
        )

    class Config:
        from_attributes = True

class QueueCreateRequest(BaseModel):
    patient_id: UUID
    doctor_id: UUID | None = None

class QueueStatusUpdateRequest(BaseModel):
    status: str

class QueueBedUpdateRequest(BaseModel):
    assigned_bed: str | None = None

class QueueCalendarResponse(BaseModel):
    counts: dict[str, int]  # {"2026-07-14": 4, ...}

class QueueCheckoutLineItem(BaseModel):
    code: str
    qty: float = 1
    days: int = 1

class QueueCheckoutRequest(BaseModel):
    kcd_code: str
    line_items: list[QueueCheckoutLineItem]