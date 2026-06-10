from uuid import UUID

from pydantic import BaseModel


class StaffCreateRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str


class StaffResponse(BaseModel):
    id: UUID
    name: str
    email: str
    role: str
    is_active: bool
