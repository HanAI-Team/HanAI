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
    symptom: str | None = None
    queue_number: int | None = None
    payment_method: str | None = None
    paid_at: datetime | None = None

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
            symptom=queue.symptom,
            queue_number=queue.queue_number,
            payment_method=queue.payment_method,
            paid_at=queue.paid_at,
        )

    class Config:
        from_attributes = True

class QueueCreateRequest(BaseModel):
    patient_id: UUID
    doctor_id: UUID | None = None
    symptom: str | None = None

class QueueStatusUpdateRequest(BaseModel):
    status: str

class QueuePayRequest(BaseModel):
    payment_method: str

class QueueBillingResponse(BaseModel):
    claim_id: UUID
    claim_amount: int
    total_amount: int
    patient_copay: int

class QueueMonthlyCountsResponse(BaseModel):
    counts: dict[str, int]