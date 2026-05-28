from uuid import UUID

from pydantic import BaseModel


class ChartingResponse(BaseModel):
    record_id: UUID
    transcription: str  # 비식별화된 텍스트
    diagnosis: str
