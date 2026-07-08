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
        )

    class Config:
        from_attributes = True

class QueueCreateRequest(BaseModel):
    patient_id: UUID
    doctor_id: UUID | None = None

class QueueStatusUpdateRequest(BaseModel):
    status: str