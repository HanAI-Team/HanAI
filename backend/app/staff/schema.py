from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class StaffCreateRequest(BaseModel):
    name: str
    username: str
    email: Optional[str] = None
    password: str
    role: str


class StaffResponse(BaseModel):
    id: UUID
    name: str
    username: str
    email: Optional[str] = None
    role: str
    is_active: bool
