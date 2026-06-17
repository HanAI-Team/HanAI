from typing import Optional
from datetime import date
from pydantic import BaseModel


class KcdUCodeResponse(BaseModel):
    code: str
    korean_name: str
    hanja: Optional[str]
    category: Optional[str]
    effective_date: Optional[date]
    expired_date: Optional[date]

    model_config = {"from_attributes": True}
