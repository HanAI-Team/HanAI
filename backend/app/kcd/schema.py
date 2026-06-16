from typing import Optional
from pydantic import BaseModel


class KcdUCodeResponse(BaseModel):
    code: str
    korean_name: str
    hanja: Optional[str]
    category: Optional[str]

    model_config = {"from_attributes": True}
