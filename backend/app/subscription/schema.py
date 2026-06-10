from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    tier: str
    status: str
    staff_limit: int

    started_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None
