from fastapi import APIRouter, Depends

from app.core.deps import get_current_doctor
from app.billing.schema import (
    PrescriptionCheckRequest,
    PrescriptionCheckResponse,
    ViolationItem,
)

router = APIRouter(tags=["billing"])

# 심평원 기준 상수
_GAMI_MAX_TYPES = 5       # 가미제 추가 약재 최대 종수
_GAMI_MAX_DOSAGE_G = 10.0 # 가미제 추가 약재 1일 최대 용량(g)
_IMP_MAX_TYPES = 15       # 임의처방 최대 종수
_IMP_MAX_DOSAGE_G = 50.0  # 임의처방 총 최대 용량(g)
_IMP_MAX_PRICE_WON = 3000 # 임의처방 최대 비용(원)


@router.post("/prescription/check", response_model=PrescriptionCheckResponse)
async def check_prescription(
    body: PrescriptionCheckRequest,
    current_doctor=Depends(get_current_doctor),
):
    """임의·가감 처방 점검 (심평원 한방 전용 기준)."""
    violations: list[ViolationItem] = []

    if body.type == "가미제":
        if len(body.herbs) > _GAMI_MAX_TYPES:
            violations.append(ViolationItem(
                rule="가미제 종수 초과",
                detail=f"가미 약재는 1일 {_GAMI_MAX_TYPES}종 이하여야 합니다. (현재 {len(body.herbs)}종)",
            ))
        for herb in body.herbs:
            if herb.dosage_g > _GAMI_MAX_DOSAGE_G:
                violations.append(ViolationItem(
                    rule="가미제 용량 초과",
                    detail=f"{herb.name}: 1일 {_GAMI_MAX_DOSAGE_G}g 이하여야 합니다. (현재 {herb.dosage_g}g)",
                ))

    elif body.type == "임의처방":
        if len(body.herbs) > _IMP_MAX_TYPES:
            violations.append(ViolationItem(
                rule="임의처방 종수 초과",
                detail=f"임의처방은 {_IMP_MAX_TYPES}종 이하여야 합니다. (현재 {len(body.herbs)}종)",
            ))
        total_dosage = sum(h.dosage_g for h in body.herbs)
        if total_dosage > _IMP_MAX_DOSAGE_G:
            violations.append(ViolationItem(
                rule="임의처방 총 용량 초과",
                detail=f"총 용량이 {_IMP_MAX_DOSAGE_G}g을 초과합니다. (현재 {total_dosage}g)",
            ))
        herbs_with_price = [h for h in body.herbs if h.price_won is not None]
        if herbs_with_price:
            total_price = sum(h.price_won for h in herbs_with_price)  # type: ignore[misc]
            if total_price > _IMP_MAX_PRICE_WON:
                violations.append(ViolationItem(
                    rule="임의처방 비용 초과",
                    detail=f"임의처방 비용이 {_IMP_MAX_PRICE_WON}원을 초과합니다. (현재 {total_price:.0f}원)",
                ))

    return PrescriptionCheckResponse(valid=len(violations) == 0, violations=violations)
