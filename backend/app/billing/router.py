from uuid import UUID

from app.billing.copayment import (
    BillingInput,
    InsuranceType,
    MedicalAidGrade,
    VisitType,
    calculate_billing,
)
from app.billing.pediatric_dosage import get_max_allowed_ratio
from app.billing.schema import (
    INSURANCE_TYPE_CHOICES,
    MEDICAL_AID_GRADE_CHOICES,
    BillingCalcRequest,
    BillingCalcResponse,
    FeeItem,
    PrescriptionCheckRequest,
    PrescriptionCheckResponse,
    ViolationItem,
)
from app.billing.service import generate_claim_edi
from app.core.database import get_db
from app.core.deps import get_current_doctor, get_current_user
from app.core.models import FeeMaster
from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["billing"])

# 심평원 기준 상수 (성인 기준)
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
    """임의·가감 처방 점검 (심평원 한방 전용 기준).

    type 종류:
      - 기준처방: 가감 없는 순수 기준처방. 한도 검증 대상 아님.
      - 가감처방: 기준처방 + 가미(added)/감미(removed). 가미 약재만 한도 검증.
      - 가미제: (기존 호환용) 모든 herbs를 가미 약재로 취급.
      - 임의처방: 한의사 임의 조합. 종수/용량/비용 모두 한도 검증.

    환자가 소아인 경우(patient_birth_date 지정), 한도값에 연령별 허용 비율을
    곱하여 검증한다. 2014.1.1. 고시 기준 기본 비율의 2배까지 처방이
    허용되므로, get_max_allowed_ratio()로 산출한 비율을 한도에 곱한다.
    """
    violations: list[ViolationItem] = []

    # 소아 환자라면 한도값에 적용할 비율 계산 (성인은 1.0 → 한도 그대로)
    dosage_ratio = get_max_allowed_ratio(body.patient_birth_date)
    gami_max_types = _GAMI_MAX_TYPES  # 종수 한도는 비율 적용 대상 아님 (용량/금액만 적용)
    gami_max_dosage_g = _GAMI_MAX_DOSAGE_G * dosage_ratio
    imp_max_types = _IMP_MAX_TYPES
    imp_max_dosage_g = _IMP_MAX_DOSAGE_G * dosage_ratio
    imp_max_price_won = _IMP_MAX_PRICE_WON * dosage_ratio

    if body.type == "기준처방":
        # 가감 없는 순수 기준처방 — 한도 초과 가능성 없음, 검증 통과
        pass

    elif body.type == "가감처방":
        # 한도 검증 대상은 '가미(added)'된 약재뿐. base/removed는 한도와 무관.
        added_herbs = [h for h in body.herbs if h.role == "added"]

        if len(added_herbs) > gami_max_types:
            violations.append(ViolationItem(
                rule="가감처방 가미 종수 초과",
                detail=f"가미 약재는 1일 {gami_max_types}종 이하여야 합니다. (현재 {len(added_herbs)}종)",
            ))

        total_added_dosage = sum(h.dosage_g for h in added_herbs)
        if total_added_dosage > gami_max_dosage_g:
            violations.append(ViolationItem(
                rule="가감처방 가미 용량 초과",
                detail=(
                    f"가미 약재 총 용량이 1일 {gami_max_dosage_g:.2f}g을 초과합니다. "
                    f"(현재 {total_added_dosage}g)"
                ),
            ))

    elif body.type == "가미제":
        # 기존 동작 유지: herbs 전체를 가미 약재로 취급
        if len(body.herbs) > gami_max_types:
            violations.append(ViolationItem(
                rule="가미제 종수 초과",
                detail=f"가미 약재는 1일 {gami_max_types}종 이하여야 합니다. (현재 {len(body.herbs)}종)",
            ))
        for herb in body.herbs:
            if herb.dosage_g > gami_max_dosage_g:
                violations.append(ViolationItem(
                    rule="가미제 용량 초과",
                    detail=(
                        f"{herb.name}: 1일 {gami_max_dosage_g:.2f}g 이하여야 합니다. "
                        f"(현재 {herb.dosage_g}g)"
                    ),
                ))

    elif body.type == "임의처방":
        if len(body.herbs) > imp_max_types:
            violations.append(ViolationItem(
                rule="임의처방 종수 초과",
                detail=f"임의처방은 {imp_max_types}종 이하여야 합니다. (현재 {len(body.herbs)}종)",
            ))
        total_dosage = sum(h.dosage_g for h in body.herbs)
        if total_dosage > imp_max_dosage_g:
            violations.append(ViolationItem(
                rule="임의처방 총 용량 초과",
                detail=(
                    f"총 용량이 {imp_max_dosage_g:.2f}g을 초과합니다. (현재 {total_dosage}g)"
                ),
            ))
        herbs_with_price = [h for h in body.herbs if h.price_won is not None]
        if herbs_with_price:
            total_price = sum(h.price_won for h in herbs_with_price)  # type: ignore[misc]
            if total_price > imp_max_price_won:
                violations.append(ViolationItem(
                    rule="임의처방 비용 초과",
                    detail=(
                        f"임의처방 비용이 {imp_max_price_won:.0f}원을 초과합니다. "
                        f"(현재 {total_price:.0f}원)"
                    ),
                ))

    return PrescriptionCheckResponse(valid=len(violations) == 0, violations=violations)


@router.post("/calculate", response_model=BillingCalcResponse)
async def calculate_copayment(
    body: BillingCalcRequest,
    current_doctor=Depends(get_current_doctor),
):
    """본인부담금 및 청구액 산정 (심사청구서 C2-00 금액 필드 30개).

    보험자종별구분에 따라 해당하는 본인부담금 항목만 값이 채워지고
    나머지 항목은 0으로 반환된다.
    """
    inp = BillingInput(
        insurance_type=InsuranceType(body.insurance_type),
        visit_type=VisitType(body.visit_type),
        benefit_total=body.benefit_total,
        non_benefit_total=body.non_benefit_total,
        special_code=body.special_code,
        medical_aid_grade=MedicalAidGrade(body.medical_aid_grade) if body.medical_aid_grade else None,
        birth_date=body.birth_date,
        treatment_date=body.treatment_date,
        work_injury=body.work_injury,
        disability_medical_cost=body.disability_medical_cost,
        support_fund=body.support_fund,
        treatment_days=body.treatment_days,
        graduated_fee_index=body.graduated_fee_index,
    )
    result = calculate_billing(inp)
    return BillingCalcResponse(special_code=body.special_code, **result.__dict__)


@router.get("/insurance-types")
async def list_insurance_types(current_doctor=Depends(get_current_doctor)):
    """보험자종별구분 선택지 목록."""
    return {
        "insurance_types": INSURANCE_TYPE_CHOICES,
        "medical_aid_grades": MEDICAL_AID_GRADE_CHOICES,
    }


@router.get("/fees", response_model=list[FeeItem])
async def list_fees(
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_doctor=Depends(get_current_doctor),
):
    """행위코드 수가 목록 조회.

    category 파라미터로 필터: 침술 / 뜸 / 부항 / 추나
    """
    stmt = select(FeeMaster).where(FeeMaster.expired_date == None)  # noqa: E711
    if category:
        stmt = stmt.where(FeeMaster.category == category)
    stmt = stmt.order_by(FeeMaster.category, FeeMaster.code)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [
        FeeItem(
            code=r.code,
            name=r.name,
            category=r.category,
            insured_health=r.insured_health,
            insured_medical_aid=r.insured_medical_aid,
            insured_veterans=r.insured_veterans,
            unit_price=r.unit_price,
            is_insured=r.is_insured,
            effective_date=r.effective_date,
            expired_date=r.expired_date,
        )
        for r in rows
    ]

@router.get("/claims/{claim_id}/edi")
async def download_claim_edi(
    claim_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    edi_bytes = await generate_claim_edi(db, current_user.hospital_id, claim_id)
    
    return Response(
        content=edi_bytes,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename=claim_{claim_id}.edi"},
    )