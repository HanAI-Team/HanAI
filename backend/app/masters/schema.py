from app.billing.schema import DrugMasterResponse, FeeItem
from pydantic import BaseModel, ConfigDict


class FeeListResponse(BaseModel):
    total: int
    page: int
    size: int
    items: list[FeeItem]


class DrugListResponse(BaseModel):
    total: int
    page: int
    size: int
    items: list[DrugMasterResponse]


class ClaimRejectionCodeItem(BaseModel):
    """billing.schema.ClaimRejectionCodeResponse에는 id가 없어(복합키로 조회하는
    /api/billing/rejection-codes 용) 삭제 버튼에 필요한 id를 포함해 별도 정의."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    category: str
    code: str
    detail_code: str
    description: str


class RejectionCodeListResponse(BaseModel):
    total: int
    page: int
    size: int
    items: list[ClaimRejectionCodeItem]
