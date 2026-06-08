from typing import Optional
from uuid import UUID
from pydantic import BaseModel, model_validator


class FeedbackCreate(BaseModel):
    medical_record_id: UUID
    is_helpful: bool
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: UUID
    is_helpful: bool
    comment: Optional[str] = None

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def convert_score(cls, data):
        if hasattr(data, "score"):
            data.__dict__["is_helpful"] = data.score == 5
        return data
