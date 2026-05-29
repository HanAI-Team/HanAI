from datetime import datetime
from pydantic import BaseModel, ConfigDict


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    tier: str
    status: str
    started_at: datetime
    expired_at: datetime | None
    is_active: bool
