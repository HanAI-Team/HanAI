from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class HospitalUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    institution_code: Optional[str] = None


class HospitalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    institution_code: Optional[str] = None
