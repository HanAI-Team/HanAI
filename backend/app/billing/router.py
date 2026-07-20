from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from app.billing import payment_service
from app.billing.catalog import (
    BILLABLE_CATALOG,
    CHUNA_50_CODES,
    CHUNA_80_CODES,
    get_catalog_item,
)
from app.billing.copayment import (
    BillingInput,
    InsuranceType,
    MedicalAidGrade,
    VisitType,
    calculate_billing,
)
from app.core.csv_export import csv_response
from app.billing.pediatric_dosage import get_max_allowed_ratio
from app.billing.schema import (
    INSURANCE_TYPE_CHOICES,
    MEDICAL_AID_GRADE_CHOICES,
    AcupointRef,
    AddLineItemsRequest,
    BillableItemResponse,
    BillingCalcRequest,
    BillingCalcResponse,
    ClaimApprovalUpdateRequest,
    ClaimBillingAgentUpdateRequest,
    ClaimLineItemResponse,
    ClaimPaymentCreateRequest,
    ClaimPaymentListResponse,
    ClaimPaymentResponse,
    ClaimPaymentSummaryResponse,
    ClaimPrescriptionResponse,
    ClaimRejectionCodeCreate,
    ClaimRejectionCodeResponse,
    ClaimRejectionCodeUpdate,
    ClaimResubmissionResponse,
    ClaimResubmissionUpdate,
    ClaimReviewResultListResponse,
    ClaimReviewResultResponse,
    ClaimReviewResultUploadResponse,
    ClaimStatementResponse,
    ClaimSummaryResponse,
    CheckoutPreviewRequest,
    CheckoutPreviewResponse,
    DoctorWorkDaysCreate,
    DoctorWorkDaysItem,
    DoctorWorkDaysUpdate,
    DrugMasterCreate,
    DrugMasterResponse,
    DrugMasterUpdate,
    FeeCreate,
    FeeItem,
    FeeUpdate,
    MaterialCreate,
    MaterialItem,
    MaterialUpdate,
    NeedsReviewClaimItem,
    NeedsReviewClaimsResponse,
    PrescriptionCheckRequest,
    PrescriptionCheckResponse,
    QuickFeeItemsResponse,
    ViolationItem,
)
from app.billing.service import (
    _INSURANCE_MAP,
    build_claim_prescription,
    build_claim_statement,
    create_claim,
    create_review_results_from_csv,
    generate_claim_edi,
    generate_claim_sam_files,
    get_quick_fee_items as service_get_quick_fee_items,
    preview_checkout_billing,
    resolve_active_special_code,
    resolve_and_validate_acupoints,
    update_claim_resubmission,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_doctor, get_current_user
from app.core.models import (
    Claim,
    ClaimLineItem,
    ClaimLineItemAcupoint,
    ClaimPayment,
    ClaimRejectionCode,
    ClaimReviewResult,
    DailyQueue,
    DoctorWorkDays,
    DrugMaster,
    FeeMaster,
    MedicalRecord,
    Patient,
)
from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, Response, UploadFile
from app.core.models import Claim, ClaimLineItem, ClaimRejectionCode, DoctorWorkDays, DrugMaster, FeeMaster, MaterialMaster, MedicalRecord, Patient
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

router = APIRouter(tags=["billing"])


class ClaimListItem(BaseModel):
    id: str
    patient_name: str
    claim_period: str
    status: str
    total_amount: int
    patient_copay: int
    claim_amount: int
    created_at: str
    special_case_review_reason: str | None = None
    approval_no: str | None = None
    from_reception: bool = False  # 접수 대시보드 청구 모달에서 생성된 청구인지 여부
    is_paid: bool = False         # from_reception 건에 한해 수납 완료 여부
    claim_type: str | None = None
    original_receipt_no: int | None = None
    original_record_serial: int | None = None
    rejection_reason_code: str | None = None
    billing_agent_code: str | None = None
    billing_agent_name: str | None = None


class ClaimCreateRequest(BaseModel):
    patient_id: str
    medical_record_ids: list[str]
    claim_period_year: int
    claim_period_month: int
    visit_type: str = "외래"  # "외래" 또는 "입원" (VisitType enum과 일치)
    approval_no: str | None
    approval_no: str | None = None
    billing_agent_code: str | None = None
    billing_agent_name: str | None = None


class ClaimCreateResponse(BaseModel):
    id: str
    status: str
    total_amount: int
    patient_copay: int
    claim_amount: int
    needs_review: bool = False


class BulkEdiRequest(BaseModel):
    ids: list[str]
    test_mode: bool = False


@router.post("/claims", response_model=ClaimCreateResponse, status_code=201)
async def create_new_claim(
    body: ClaimCreateRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from uuid import UUID as _UUID
    claim = await create_claim(
        db=db,
        hospital_id=current_user.hospital_id,
        doctor_id=current_user.id,
        patient_id=_UUID(body.patient_id),
        medical_record_ids=[_UUID(rid) for rid in body.medical_record_ids],
        claim_period_year=body.claim_period_year,
        claim_period_month=body.claim_period_month,
        visit_type=body.visit_type,
        approval_no=body.approval_no,
        billing_agent_code=body.billing_agent_code,
        billing_agent_name=body.billing_agent_name,
    )
    return ClaimCreateResponse(
        id=str(claim.id),
        status=claim.status,
        total_amount=claim.total_amount,
        patient_copay=claim.patient_copay,
        claim_amount=claim.claim_amount,
        needs_review=getattr(claim, "special_case_review_reason", None) is not None,
    )


@router.get("/claims", response_model=list[ClaimListItem])
async def list_claims(
    month: str | None = Query(None, description="YYYY-MM 형식, 예: 2026-06"),
    status: str | None = Query(None, description="draft / submitted / approved / rejected"),
    needs_review: bool | None = Query(None, description="True면 review_reason이 있는 청구만"),
    review_reason: str | None = Query(None, description="review_reason에 포함된 사유로 필터 (부분일치)"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Claim, Patient)
        .join(Patient, Claim.patient_id == Patient.id)
        .where(Claim.hospital_id == current_user.hospital_id)
    )
    if month:
        year, mon = int(month[:4]), int(month[5:7])
        stmt = stmt.where(Claim.claim_period_year == year, Claim.claim_period_month == mon)
    if status:
        stmt = stmt.where(Claim.status == status)
    if needs_review is not None:
        if needs_review:
            stmt = stmt.where(Claim.special_case_review_reason.isnot(None))
        else:
            stmt = stmt.where(Claim.special_case_review_reason.is_(None))
    if review_reason:
        stmt = stmt.where(Claim.special_case_review_reason.like(f"%{review_reason}%"))
    stmt = stmt.order_by(Claim.created_at.desc())

    rows = await db.execute(stmt)
    results = rows.all()

    claim_ids = [claim.id for claim, _ in results]
    reception_claim_ids: set = set()
    paid_claim_ids: set = set()
    if claim_ids:
        r_reception = await db.execute(
            select(DailyQueue.claim_id).where(DailyQueue.claim_id.in_(claim_ids))
        )
        reception_claim_ids = {cid for cid, in r_reception.all()}
        r_paid = await db.execute(
            select(ClaimPayment.claim_id).where(ClaimPayment.claim_id.in_(claim_ids)).distinct()
        )
        paid_claim_ids = {cid for cid, in r_paid.all()}

    return [
        ClaimListItem(
            id=str(claim.id),
            patient_name=patient.name,
            claim_period=f"{claim.claim_period_year}-{claim.claim_period_month:02d}",
            status=claim.status,
            total_amount=claim.total_amount,
            patient_copay=claim.patient_copay,
            claim_amount=claim.claim_amount,
            created_at=claim.created_at.strftime("%Y-%m-%d") if claim.created_at else "",
            special_case_review_reason=claim.special_case_review_reason,
            approval_no=claim.approval_no,
            from_reception=claim.id in reception_claim_ids,
            is_paid=claim.id in paid_claim_ids,
            claim_type=claim.claim_type,
            original_receipt_no=claim.original_receipt_no,
            original_record_serial=claim.original_record_serial,
            rejection_reason_code=claim.rejection_reason_code,
            billing_agent_code=claim.billing_agent_code,
            billing_agent_name=claim.billing_agent_name,
        )
        for claim, patient in results
    ]


@router.get("/claims/needs-review", response_model=NeedsReviewClaimsResponse)
async def list_needs_review_claims(
    review_reason: str | None = Query(None, description="review_reason에 포함된 사유로 필터 (부분일치)"),
    month: str | None = Query(None, description="YYYY-MM 형식, 예: 2026-06"),
    page: int = 1,
    size: int = 20,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    base_query = select(Claim).where(
        Claim.hospital_id == current_user.hospital_id,
        Claim.special_case_review_reason.isnot(None),
    )
    if review_reason:
        base_query = base_query.where(Claim.special_case_review_reason.like(f"%{review_reason}%"))
    if month:
        year, mon = int(month[:4]), int(month[5:7])
        base_query = base_query.where(
            Claim.claim_period_year == year, Claim.claim_period_month == mon
        )

    count_result = await db.execute(select(func.count()).select_from(base_query.subquery()))
    total = count_result.scalar_one()

    stmt = (
        base_query.options(selectinload(Claim.patient))
        .order_by(Claim.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    rows = await db.execute(stmt)
    claims = rows.scalars().all()

    return NeedsReviewClaimsResponse(
        total=total,
        items=[
            NeedsReviewClaimItem(
                id=claim.id,
                patient_id=claim.patient_id,
                patient_name=claim.patient.name,
                claim_period_year=claim.claim_period_year,
                claim_period_month=claim.claim_period_month,
                special_case_review_reason=claim.special_case_review_reason,
                status=claim.status,
                total_amount=claim.total_amount,
                created_at=claim.created_at,
            )
            for claim in claims
        ],
    )


@router.patch("/claims/{claim_id}/resubmission", response_model=ClaimResubmissionResponse)
async def patch_claim_resubmission(
    claim_id: UUID,
    body: ClaimResubmissionUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    claim = await update_claim_resubmission(
        db=db,
        hospital_id=current_user.hospital_id,
        actor_id=current_user.id,
        claim_id=claim_id,
        claim_type=body.claim_type,
        original_receipt_no=body.original_receipt_no,
        original_record_serial=body.original_record_serial,
        rejection_reason_code=body.rejection_reason_code,
    )
    return ClaimResubmissionResponse(
        id=str(claim.id),
        status=claim.status,
        claim_type=claim.claim_type,
        original_receipt_no=claim.original_receipt_no,
        original_record_serial=claim.original_record_serial,
        rejection_reason_code=claim.rejection_reason_code,
    )


@router.post("/claims/bulk-edi")
async def bulk_download_edi(
    body: BulkEdiRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for claim_id_str in body.ids:
            edi_bytes = await generate_claim_edi(db, current_user.hospital_id, UUID(claim_id_str), test_mode=body.test_mode)
            suffix = "_TEST" if body.test_mode else ""
            zf.writestr(f"claim_{claim_id_str}{suffix}.sam", edi_bytes)
    buf.seek(0)

    filename = "claims_edi_TEST.zip" if body.test_mode else "claims_edi.zip"
    return Response(
        content=buf.read(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Cache-Control": "no-store",
        },
    )


@router.post("/claims/review-results/upload", response_model=ClaimReviewResultUploadResponse)
async def upload_review_results(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """심사결과(수신) CSV 업로드. 실제 심평원 EDI 수신 연동 전까지의 임시 경로."""
    content = await file.read()
    inserted, skipped = await create_review_results_from_csv(db, current_user.hospital_id, content)
    return ClaimReviewResultUploadResponse(inserted=inserted, skipped=skipped)


@router.get("/claims/review-results", response_model=ClaimReviewResultListResponse)
async def list_review_results(
    start_date: date | None = Query(None, description="심사일자 시작 (YYYY-MM-DD)"),
    end_date: date | None = Query(None, description="심사일자 종료 (YYYY-MM-DD)"),
    result_code: str | None = Query(None, description="인정 | 삭감 | 보류"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    base_query = select(ClaimReviewResult).where(
        ClaimReviewResult.hospital_id == current_user.hospital_id
    )
    if start_date:
        base_query = base_query.where(ClaimReviewResult.review_date >= start_date)
    if end_date:
        base_query = base_query.where(ClaimReviewResult.review_date <= end_date)
    if result_code:
        base_query = base_query.where(ClaimReviewResult.result_code == result_code)

    total_result = await db.execute(select(func.count()).select_from(base_query.subquery()))
    total = total_result.scalar_one()

    stmt = (
        base_query.order_by(ClaimReviewResult.review_date.desc(), ClaimReviewResult.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    rows = await db.execute(stmt)
    items = rows.scalars().all()

    return ClaimReviewResultListResponse(
        total=total,
        page=page,
        size=size,
        items=[ClaimReviewResultResponse.model_validate(item) for item in items],
    )


@router.get("/claims/review-results/{result_id}", response_model=ClaimReviewResultResponse)
async def get_review_result(
    result_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(ClaimReviewResult, result_id)
    if not item or item.hospital_id != current_user.hospital_id:
        raise HTTPException(status_code=404, detail="심사결과를 찾을 수 없습니다.")
    return ClaimReviewResultResponse.model_validate(item)


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
    db: AsyncSession = Depends(get_db),
):
    """본인부담금 및 청구액 산정 (심사청구서 C2-00 금액 필드 30개).

    보험자종별구분에 따라 해당하는 본인부담금 항목만 값이 채워지고
    나머지 항목은 0으로 반환된다.

    patient_id가 주어지면 활성 산정특례 등록을 조회해 body.special_code보다
    우선 적용한다 (등록이 없으면 body.special_code 그대로 사용).
    """
    needs_review = False
    special_code = body.special_code
    if body.patient_id is not None:
        resolved = await resolve_active_special_code(db, body.patient_id)
        if resolved.special_code is not None:
            special_code = resolved.special_code
            needs_review = resolved.review_reason is not None

    inp = BillingInput(
        insurance_type=InsuranceType(body.insurance_type),
        visit_type=VisitType(body.visit_type),
        benefit_total=body.benefit_total,
        non_benefit_total=body.non_benefit_total,
        special_code=special_code,
        medical_aid_grade=MedicalAidGrade(body.medical_aid_grade) if body.medical_aid_grade else None,
        birth_date=body.birth_date,
        treatment_date=body.treatment_date,
        work_injury=body.work_injury,
        has_disability=body.has_disability,
        support_fund=body.support_fund,
        treatment_days=body.treatment_days,
        graduated_fee_index=body.graduated_fee_index,
        exam_fee=body.exam_fee,
    )
    result = calculate_billing(inp)
    return BillingCalcResponse(special_code=special_code, needs_review=needs_review, **result.__dict__)


@router.get("/insurance-types")
async def list_insurance_types(current_doctor=Depends(get_current_doctor)):
    """보험자종별구분 선택지 목록."""
    return {
        "insurance_types": INSURANCE_TYPE_CHOICES,
        "medical_aid_grades": MEDICAL_AID_GRADE_CHOICES,
    }


@router.get("/rejection-codes", response_model=list[ClaimRejectionCodeResponse])
async def search_rejection_codes(
    q: str = Query(..., min_length=1, description="코드 또는 사유 내용 검색어"),
    category: Optional[str] = Query(None, description="반송 | 심사불능 | 수탁기관통보"),
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """요양급여비용 심사보류·불능·반송 사유별 코드(별첨6) 및 수탁기관 통보 사유코드(별첨7) 검색."""
    stmt = select(ClaimRejectionCode).where(
        or_(
            ClaimRejectionCode.code.ilike(f"{q}%"),
            ClaimRejectionCode.description.ilike(f"%{q}%"),
        )
    )
    if category:
        stmt = stmt.where(ClaimRejectionCode.category == category)
    stmt = stmt.order_by(ClaimRejectionCode.category, ClaimRejectionCode.code, ClaimRejectionCode.detail_code).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/rejection-codes", response_model=ClaimRejectionCodeResponse, status_code=201)
async def create_rejection_code(
    body: ClaimRejectionCodeCreate,
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
    db: AsyncSession = Depends(get_db),
):
    _check_admin(x_admin_key)
    existing = await db.execute(
        select(ClaimRejectionCode).where(
            ClaimRejectionCode.category == body.category,
            ClaimRejectionCode.code == body.code,
            ClaimRejectionCode.detail_code == body.detail_code,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="이미 존재하는 코드입니다.")
    item = ClaimRejectionCode(**body.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.put("/rejection-codes/{item_id}", response_model=ClaimRejectionCodeResponse)
async def update_rejection_code(
    item_id: int,
    body: ClaimRejectionCodeUpdate,
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
    db: AsyncSession = Depends(get_db),
):
    # detail_code가 ""(빈 문자열)인 행이 많아 category/code/detail_code 복합키 대신
    # 정수 id를 식별자로 사용 (빈 문자열은 URL 경로 세그먼트로 다루기 까다로움).
    _check_admin(x_admin_key)
    item = await db.get(ClaimRejectionCode, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="코드를 찾을 수 없습니다.")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(item, field, value)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/rejection-codes/{item_id}", status_code=204)
async def delete_rejection_code(
    item_id: int,
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
    db: AsyncSession = Depends(get_db),
):
    _check_admin(x_admin_key)
    item = await db.get(ClaimRejectionCode, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="코드를 찾을 수 없습니다.")
    await db.delete(item)
    await db.commit()


@router.get("/rejection-codes/export")
async def export_rejection_codes(
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
    db: AsyncSession = Depends(get_db),
):
    """반송·심사불능 코드 마스터 전체를 CSV(TEXT/Excel)로 추출."""
    _check_admin(x_admin_key)
    result = await db.execute(
        select(ClaimRejectionCode).order_by(
            ClaimRejectionCode.category, ClaimRejectionCode.code, ClaimRejectionCode.detail_code
        )
    )
    rows = [[r.category, r.code, r.detail_code, r.description] for r in result.scalars().all()]
    return csv_response(
        "rejection_codes.csv", ["category", "code", "detail_code", "description"], rows
    )


@router.get("/drugs", response_model=list[DrugMasterResponse])
async def search_drugs(
    q: str = Query(..., min_length=1, description="제품코드, 제품명 또는 주성분명 검색어"),
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """약제급여목록 및 급여상한금액표 검색 (제품코드/제품명/주성분명)."""
    stmt = select(DrugMaster).where(
        or_(
            DrugMaster.product_code.ilike(f"{q}%"),
            DrugMaster.product_name.ilike(f"%{q}%"),
            DrugMaster.ingredient_name.ilike(f"%{q}%"),
        )
    )
    stmt = stmt.order_by(DrugMaster.product_name).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/drugs", response_model=DrugMasterResponse, status_code=201)
async def create_drug(
    body: DrugMasterCreate,
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
    db: AsyncSession = Depends(get_db),
):
    _check_admin(x_admin_key)
    existing = await db.execute(select(DrugMaster).where(DrugMaster.product_code == body.product_code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="이미 존재하는 제품코드입니다.")
    drug = DrugMaster(**body.model_dump())
    db.add(drug)
    await db.commit()
    await db.refresh(drug)
    return drug


@router.put("/drugs/{product_code}", response_model=DrugMasterResponse)
async def update_drug(
    product_code: str,
    body: DrugMasterUpdate,
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
    db: AsyncSession = Depends(get_db),
):
    _check_admin(x_admin_key)
    result = await db.execute(select(DrugMaster).where(DrugMaster.product_code == product_code))
    drug = result.scalar_one_or_none()
    if not drug:
        raise HTTPException(status_code=404, detail="제품코드를 찾을 수 없습니다.")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(drug, field, value)
    await db.commit()
    await db.refresh(drug)
    return drug


@router.delete("/drugs/{product_code}", status_code=204)
async def delete_drug(
    product_code: str,
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
    db: AsyncSession = Depends(get_db),
):
    _check_admin(x_admin_key)
    result = await db.execute(select(DrugMaster).where(DrugMaster.product_code == product_code))
    drug = result.scalar_one_or_none()
    if not drug:
        raise HTTPException(status_code=404, detail="제품코드를 찾을 수 없습니다.")
    await db.delete(drug)
    await db.commit()


@router.get("/drugs/export")
async def export_drugs(
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
    db: AsyncSession = Depends(get_db),
):
    """약가 마스터 전체를 CSV(TEXT/Excel)로 추출."""
    _check_admin(x_admin_key)
    result = await db.execute(select(DrugMaster).order_by(DrugMaster.product_code))
    rows = [
        [
            r.product_code, r.product_name, r.ingredient_code, r.ingredient_name,
            r.company_name, r.spec, r.unit, r.unit_price, r.administration_route,
            r.classification_code, r.is_prescription, r.effective_date,
        ]
        for r in result.scalars().all()
    ]
    header = [
        "product_code", "product_name", "ingredient_code", "ingredient_name",
        "company_name", "spec", "unit", "unit_price", "administration_route",
        "classification_code", "is_prescription", "effective_date",
    ]
    return csv_response("drug_master.csv", header, rows)


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
    return [_fee_to_item(r) for r in rows]


def _fee_to_item(r: FeeMaster) -> FeeItem:
    return FeeItem(
        code=r.code,
        name=r.name,
        category=r.category,
        insured_health=r.insured_health,
        insured_medical_aid=r.insured_medical_aid,
        insured_veterans=r.insured_veterans,
        unit_price=r.unit_price,
        is_insured=r.is_insured,
        is_standalone=r.is_standalone,
        effective_date=r.effective_date,
        expired_date=r.expired_date,
    )


def _check_admin(key: str) -> None:
    if key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="관리자 키가 올바르지 않습니다.")


@router.post("/fees", response_model=FeeItem, status_code=201)
async def create_fee(
    body: FeeCreate,
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
    db: AsyncSession = Depends(get_db),
):
    _check_admin(x_admin_key)
    existing = await db.execute(select(FeeMaster).where(FeeMaster.code == body.code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="이미 존재하는 행위코드입니다.")
    fee = FeeMaster(**body.model_dump())
    db.add(fee)
    await db.commit()
    await db.refresh(fee)
    return _fee_to_item(fee)


@router.put("/fees/{code}", response_model=FeeItem)
async def update_fee(
    code: str,
    body: FeeUpdate,
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
    db: AsyncSession = Depends(get_db),
):
    _check_admin(x_admin_key)
    result = await db.execute(select(FeeMaster).where(FeeMaster.code == code))
    fee = result.scalar_one_or_none()
    if not fee:
        raise HTTPException(status_code=404, detail="수가 코드를 찾을 수 없습니다.")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(fee, field, value)
    await db.commit()
    await db.refresh(fee)
    return _fee_to_item(fee)


@router.delete("/fees/{code}", status_code=204)
async def delete_fee(
    code: str,
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
    db: AsyncSession = Depends(get_db),
):
    _check_admin(x_admin_key)
    result = await db.execute(select(FeeMaster).where(FeeMaster.code == code))
    fee = result.scalar_one_or_none()
    if not fee:
        raise HTTPException(status_code=404, detail="수가 코드를 찾을 수 없습니다.")
    await db.delete(fee)
    await db.commit()


@router.get("/fees/export")
async def export_fees(
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
    db: AsyncSession = Depends(get_db),
):
    """한방 행위코드 수가 마스터 전체를 CSV(TEXT/Excel)로 추출."""
    _check_admin(x_admin_key)
    result = await db.execute(select(FeeMaster).order_by(FeeMaster.category, FeeMaster.code))
    rows = [
        [
            r.code, r.name, r.category, r.insured_health, r.insured_medical_aid,
            r.insured_veterans, r.unit_price, r.is_insured, r.is_standalone,
            r.effective_date, r.expired_date,
        ]
        for r in result.scalars().all()
    ]
    header = [
        "code", "name", "category", "insured_health", "insured_medical_aid",
        "insured_veterans", "unit_price", "is_insured", "is_standalone",
        "effective_date", "expired_date",
    ]
    return csv_response("fee_master.csv", header, rows)


@router.get("/materials", response_model=list[MaterialItem])
async def list_materials(
    db: AsyncSession = Depends(get_db),
    current_doctor=Depends(get_current_doctor),
):
    """치료재료대 마스터 목록 조회."""
    stmt = (
        select(MaterialMaster)
        .where(MaterialMaster.expired_date == None)  # noqa: E711
        .order_by(MaterialMaster.code)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/materials", response_model=MaterialItem, status_code=201)
async def create_material(
    body: MaterialCreate,
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
    db: AsyncSession = Depends(get_db),
):
    _check_admin(x_admin_key)
    existing = await db.execute(select(MaterialMaster).where(MaterialMaster.code == body.code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="이미 존재하는 치료재료 코드입니다.")
    material = MaterialMaster(**body.model_dump())
    db.add(material)
    await db.commit()
    await db.refresh(material)
    return material


@router.put("/materials/{code}", response_model=MaterialItem)
async def update_material(
    code: str,
    body: MaterialUpdate,
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
    db: AsyncSession = Depends(get_db),
):
    _check_admin(x_admin_key)
    result = await db.execute(select(MaterialMaster).where(MaterialMaster.code == code))
    material = result.scalar_one_or_none()
    if not material:
        raise HTTPException(status_code=404, detail="치료재료 코드를 찾을 수 없습니다.")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(material, field, value)
    await db.commit()
    await db.refresh(material)
    return material


@router.delete("/materials/{code}", status_code=204)
async def delete_material(
    code: str,
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
    db: AsyncSession = Depends(get_db),
):
    _check_admin(x_admin_key)
    result = await db.execute(select(MaterialMaster).where(MaterialMaster.code == code))
    material = result.scalar_one_or_none()
    if not material:
        raise HTTPException(status_code=404, detail="치료재료 코드를 찾을 수 없습니다.")
    await db.delete(material)
    await db.commit()


def _work_days_to_item(r: DoctorWorkDays) -> DoctorWorkDaysItem:
    return DoctorWorkDaysItem(
        id=r.id,
        claim_period_year=r.claim_period_year,
        claim_period_month=r.claim_period_month,
        doctor_birth_date=r.doctor_birth_date,
        work_days=r.work_days,
    )


@router.get("/doctor-work-days", response_model=list[DoctorWorkDaysItem])
async def list_doctor_work_days(
    year: int | None = Query(None, description="청구년도, 예: 2026"),
    month: int | None = Query(None, ge=1, le=12, description="청구월, 예: 7"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """MT008(의사별 진료일수) 원본 데이터 조회. year/month 지정 시 해당 청구월만 필터."""
    stmt = select(DoctorWorkDays).where(DoctorWorkDays.hospital_id == current_user.hospital_id)
    if year:
        stmt = stmt.where(DoctorWorkDays.claim_period_year == year)
    if month:
        stmt = stmt.where(DoctorWorkDays.claim_period_month == month)
    stmt = stmt.order_by(
        DoctorWorkDays.claim_period_year.desc(),
        DoctorWorkDays.claim_period_month.desc(),
        DoctorWorkDays.id,
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [_work_days_to_item(r) for r in rows]


@router.post("/doctor-work-days", response_model=DoctorWorkDaysItem, status_code=201)
async def create_doctor_work_days(
    body: DoctorWorkDaysCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """MT008(의사별 진료일수) 원본 데이터 입력.

    같은 병원·같은 청구년월·같은 의사생년월일 조합이 이미 있으면 409로 막는다
    (실수로 같은 의사를 중복 입력해 EDI에 두 번 찍히는 것을 방지).
    """
    existing = await db.execute(
        select(DoctorWorkDays).where(
            DoctorWorkDays.hospital_id == current_user.hospital_id,
            DoctorWorkDays.claim_period_year == body.claim_period_year,
            DoctorWorkDays.claim_period_month == body.claim_period_month,
            DoctorWorkDays.doctor_birth_date == body.doctor_birth_date,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="해당 청구년월·의사생년월일 조합의 진료일수가 이미 등록되어 있습니다.",
        )

    row = DoctorWorkDays(
        hospital_id=current_user.hospital_id,
        claim_period_year=body.claim_period_year,
        claim_period_month=body.claim_period_month,
        doctor_birth_date=body.doctor_birth_date,
        work_days=body.work_days,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _work_days_to_item(row)


@router.put("/doctor-work-days/{work_days_id}", response_model=DoctorWorkDaysItem)
async def update_doctor_work_days(
    work_days_id: int,
    body: DoctorWorkDaysUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DoctorWorkDays).where(
            DoctorWorkDays.id == work_days_id,
            DoctorWorkDays.hospital_id == current_user.hospital_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="진료일수 데이터를 찾을 수 없습니다.")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(row, field, value)
    await db.commit()
    await db.refresh(row)
    return _work_days_to_item(row)


@router.delete("/doctor-work-days/{work_days_id}", status_code=204)
async def delete_doctor_work_days(
    work_days_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DoctorWorkDays).where(
            DoctorWorkDays.id == work_days_id,
            DoctorWorkDays.hospital_id == current_user.hospital_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="진료일수 데이터를 찾을 수 없습니다.")
    await db.delete(row)
    await db.commit()


@router.get("/claims/{claim_id}/edi")
async def download_claim_edi(
    claim_id: UUID,
    test: bool = Query(False, description="True이면 작성자란에 '상시점검' 기재한 테스트 SAM FILE 생성"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    edi_bytes = await generate_claim_edi(db, current_user.hospital_id, claim_id, test_mode=test)
    suffix = "_TEST" if test else ""
    return Response(
        content=edi_bytes,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename=claim_{claim_id}{suffix}.sam",
            "Cache-Control": "no-store",
        },
    )


@router.get("/claims/{claim_id}/sam-files")
async def download_claim_sam_files(
    claim_id: UUID,
    test: bool = Query(False, description="True이면 작성자란에 '상시점검' 기재한 테스트 SAM FILE 생성"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """SAM File 생성 디렉토리(/HIRA/DDMD/SAM/IN/)에 그대로 넣을 개별 파일들
    (H010, K020.1~4)을 ZIP으로 묶어 반환한다. 압축·암호화(.GHP)는 별도의
    전자청구 프로그램이 담당하므로 여기서는 원본 파일까지만 제공한다."""
    import io
    import zipfile

    files = await generate_claim_sam_files(db, current_user.hospital_id, claim_id, test_mode=test)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, content in files.items():
            zf.writestr(filename, content)
    buf.seek(0)

    suffix = "_TEST" if test else ""
    return Response(
        content=buf.read(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=claim_{claim_id}{suffix}_sam_files.zip",
            "Cache-Control": "no-store",
        },
    )


@router.get("/claims/{claim_id}/statement", response_model=ClaimStatementResponse)
async def get_claim_statement(
    claim_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """요양급여비용명세서(한방외래, 별지18호/GI013) 출력용 데이터."""
    return await build_claim_statement(db, current_user.hospital_id, claim_id)


@router.get("/claims/{claim_id}/prescription", response_model=ClaimPrescriptionResponse)
async def get_claim_prescription(
    claim_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """처방전(의료법 시행규칙 별지9호서식) 출력용 데이터."""
    return await build_claim_prescription(db, current_user.hospital_id, claim_id)


@router.post("/claims/{claim_id}/payments", response_model=ClaimPaymentResponse, status_code=201)
async def create_claim_payment(
    claim_id: UUID,
    body: ClaimPaymentCreateRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """수납 완료 처리 — 접수 목록의 상태도 함께 "수납완료"로 전환한다."""
    payment = await payment_service.create_payment(
        db,
        hospital_id=current_user.hospital_id,
        claim_id=claim_id,
        method=body.method,
        amount=body.amount,
        processed_by_name=current_user.name,
    )
    claim = await db.get(Claim, claim_id)
    patient = await db.get(Patient, claim.patient_id) if claim else None
    return ClaimPaymentResponse(
        id=payment.id,
        claim_id=payment.claim_id,
        patient_name=patient.name if patient else "-",
        method=payment.method,
        claim_amount=claim.claim_amount if claim else 0,
        amount=payment.amount,
        paid_at=payment.paid_at.strftime("%Y-%m-%d %H:%M"),
        processed_by_name=payment.processed_by_name,
    )


@router.get("/payments", response_model=ClaimPaymentListResponse)
async def list_claim_payments(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    method: str | None = Query(None, description="cash / card / transfer"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """수납 내역 모달 — 필터(날짜범위/수납방법) + 페이지네이션."""
    total, rows = await payment_service.list_payments(
        db, current_user.hospital_id, start_date, end_date, method, page, size
    )
    return ClaimPaymentListResponse(
        total=total,
        page=page,
        size=size,
        items=[
            ClaimPaymentResponse(
                id=payment.id,
                claim_id=payment.claim_id,
                patient_name=patient.name,
                method=payment.method,
                claim_amount=claim.claim_amount,
                amount=payment.amount,
                paid_at=payment.paid_at.strftime("%Y-%m-%d %H:%M"),
                processed_by_name=payment.processed_by_name,
            )
            for payment, claim, patient in rows
        ],
    )


@router.get("/payments/summary", response_model=ClaimPaymentSummaryResponse)
async def get_claim_payment_summary(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    method: str | None = Query(None, description="cash / card / transfer"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """오늘/이번달 수납액은 필터와 무관하게 항상 실제 오늘·이번달 기준.
    현금/카드 비율만 현재 필터(날짜범위+수납방법) 범위 내에서 집계."""
    summary = await payment_service.get_payment_summary(
        db, current_user.hospital_id, start_date, end_date, method
    )
    return ClaimPaymentSummaryResponse(**summary)


@router.get("/fee-quick-items", response_model=QuickFeeItemsResponse)
async def get_quick_fee_items(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """청구 모달의 카테고리 탭 + 빠른 입력 버튼 그리드 — FeeMaster 실데이터 기반."""
    return await service_get_quick_fee_items(db, current_user.hospital_id)


@router.post("/checkout-preview", response_model=CheckoutPreviewResponse)
async def preview_checkout(
    body: CheckoutPreviewRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """청구 모달에서 처방/시술 내역을 추가/삭제할 때마다 호출하는 실시간 미리보기.
    DB에 아무것도 쓰지 않으며, 실제 저장(checkout_queue_item)과 동일한
    calculate_billing() 계산 경로를 재사용한다."""
    result = await preview_checkout_billing(
        db, body.patient_id, [li.model_dump() for li in body.line_items]
    )
    return CheckoutPreviewResponse(
        total_amount=result["total_amount"],
        patient_copay=result["patient_copay"],
        claim_amount=result["claim_amount"],
        special_code=result["special_code"],
    )


@router.get("/catalog", response_model=list[BillableItemResponse])
async def get_billable_catalog(current_user=Depends(get_current_user)):
    return [
        BillableItemResponse(
            id=item.id,
            name=item.name,
            sub=item.sub,
            category=item.category,
            unitPrice=item.unit_price,
            isInsured=item.is_insured,
            requiresHyeolmyeong=item.requires_hyeolmyeong,
        )
        for item in BILLABLE_CATALOG
    ]


def _line_item_to_response(item: ClaimLineItem) -> ClaimLineItemResponse:
    """item.acupoints는 호출부에서 selectinload로 미리 로드돼 있어야 한다."""
    return ClaimLineItemResponse(
        id=str(item.id),
        name=item.name,
        code=item.code,
        amount=item.amount,
        acupoints=[
            AcupointRef(code=a.acupuncture_point_code, korean_name=a.korean_name)
            for a in sorted(item.acupoints, key=lambda a: a.display_order)
        ],
        is_non_benefit=item.is_non_benefit,
    )


@router.post("/medical-records/{record_id}/line-items", response_model=ClaimSummaryResponse)
async def add_line_items(
    record_id: UUID,
    payload: AddLineItemsRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    record = await db.get(MedicalRecord, record_id)
    if not record or record.hospital_id != current_user.hospital_id:
        raise HTTPException(status_code=404, detail="진료기록을 찾을 수 없습니다.")

    recorded = record.recorded_at or record.created_at
    year, month = recorded.year, recorded.month

    # 이번 달 draft Claim 찾거나 새로 생성
    existing = await db.execute(
        select(Claim).where(
            Claim.patient_id == record.patient_id,
            Claim.hospital_id == current_user.hospital_id,
            Claim.claim_period_year == year,
            Claim.claim_period_month == month,
            Claim.status == "draft",
        )
    )
    claim = existing.scalar_one_or_none()
    if claim is None:
        import uuid as _uuid
        claim = Claim(
            id=_uuid.uuid4(),
            patient_id=record.patient_id,
            doctor_id=current_user.id,
            hospital_id=current_user.hospital_id,
            claim_period_year=year,
            claim_period_month=month,
            total_amount=0,
            patient_copay=0,
            claim_amount=0,
            status="draft",
        )
        db.add(claim)
        await db.flush()

    added_amount = 0
    added_non_benefit = 0
    codes_in_this_request: set[str] = set()
    for line in payload.items:
        catalog_item = get_catalog_item(line.item_id)
        amount = int(Decimal(str(catalog_item.unit_price)))

        acupoints = await resolve_and_validate_acupoints(
            db, record_id, line.acupoint_codes, codes_in_this_request
        )

        line_item = ClaimLineItem(
            claim_id=claim.id,
            medical_record_id=record.id,
            hang=catalog_item.hang,
            mok=catalog_item.mok,
            code=catalog_item.code,
            name=catalog_item.name,
            unit_price=catalog_item.unit_price,
            qty=1,
            days=1,
            amount=amount,
            is_non_benefit=line.is_non_benefit,
        )
        db.add(line_item)
        await db.flush()
        for order, point in enumerate(acupoints):
            db.add(ClaimLineItemAcupoint(
                claim_line_item_id=line_item.id,
                acupuncture_point_code=point.code,
                korean_name=point.korean_name,
                display_order=order,
            ))
        added_amount += amount
        if line.is_non_benefit:
            added_non_benefit += amount

    claim.total_amount = (claim.total_amount or 0) + added_amount
    claim.non_benefit_total = (claim.non_benefit_total or 0) + added_non_benefit

    # MedicalRecord를 이 claim에 연결
    if record.claim_id != claim.id:
        record.claim_id = claim.id

    # 본인부담금 / 청구액 재계산
    patient = await db.get(Patient, record.patient_id)
    if patient:
        ins = _INSURANCE_MAP.get(patient.insurance_type or "health", InsuranceType.HEALTH)
        aid_grade = None
        if patient.medical_aid_grade == "1":
            aid_grade = MedicalAidGrade.GRADE_1
        elif patient.medical_aid_grade == "2":
            aid_grade = MedicalAidGrade.GRADE_2
        special_case = await resolve_active_special_code(db, patient.id)

        # 추나 본인부담률(50%/80%) 분리 적용을 위해 코드별로 나눠서 합산.
        # 2026-07-08 재수정: 이 파일이 한 차례 #373(요율 분리 수정) 이전 버전으로
        # 되돌아가 있었음 — CHUNA_CODES 단일 합산 + chuna_80_total 누락으로
        # 40721(80% 대상)이 다시 50%로 잘못 계산되는 회귀가 있었던 것을 재적용함.
        await db.flush()
        chuna_50_rows = await db.execute(
            select(ClaimLineItem.amount).where(
                ClaimLineItem.claim_id == claim.id,
                ClaimLineItem.is_non_benefit == False,
                ClaimLineItem.code.in_(CHUNA_50_CODES),
            )
        )
        chuna_total = sum(r.amount or 0 for r in chuna_50_rows)

        chuna_80_rows = await db.execute(
            select(ClaimLineItem.amount).where(
                ClaimLineItem.claim_id == claim.id,
                ClaimLineItem.is_non_benefit == False,
                ClaimLineItem.code.in_(CHUNA_80_CODES),
            )
        )
        chuna_80_total = sum(r.amount or 0 for r in chuna_80_rows)

        billing_result = calculate_billing(BillingInput(
            insurance_type=ins,
            visit_type=VisitType(payload.visit_type),
            benefit_total=claim.total_amount - claim.non_benefit_total,
            medical_aid_grade=aid_grade,
            has_disability=bool(patient.disability_grade),
            birth_date=patient.birth_date,
            special_code=special_case.special_code,
            chuna_total=chuna_total,
            chuna_80_total=chuna_80_total,
        ))
        claim.patient_copay = billing_result.copayment
        claim.claim_amount = billing_result.claim_amount
        claim.disability_medical_aid = billing_result.disability_medical_cost

    await db.commit()
    await db.refresh(claim)

    items_result = await db.execute(
        select(ClaimLineItem)
        .where(ClaimLineItem.claim_id == claim.id)
        .options(selectinload(ClaimLineItem.acupoints))
    )
    all_items = items_result.scalars().all()

    return ClaimSummaryResponse(
        id=str(claim.id),
        patient_id=str(claim.patient_id),
        billing_month=f"{year}-{month:02d}",
        status=claim.status,
        total_amount=claim.total_amount,
        line_items=[_line_item_to_response(i) for i in all_items],
    )


@router.patch("/claims/{claim_id}/approval")
async def update_claim_approval(
    claim_id: UUID,
    body: ClaimApprovalUpdateRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    claim = await db.get(Claim, claim_id)
    if not claim or claim.hospital_id != current_user.hospital_id:
        raise HTTPException(status_code=404, detail="청구를 찾을 수 없습니다.")
    claim.approval_no = body.approval_no
    await db.commit()
    return {"id": str(claim_id), "approval_no": claim.approval_no}


@router.patch("/claims/{claim_id}/billing-agent")
async def update_claim_billing_agent(
    claim_id: UUID,
    body: ClaimBillingAgentUpdateRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    claim = await db.get(Claim, claim_id)
    if not claim or claim.hospital_id != current_user.hospital_id:
        raise HTTPException(status_code=404, detail="청구를 찾을 수 없습니다.")
    claim.billing_agent_code = body.billing_agent_code
    claim.billing_agent_name = body.billing_agent_name
    await db.commit()
    return {
        "id": str(claim_id),
        "billing_agent_code": claim.billing_agent_code,
        "billing_agent_name": claim.billing_agent_name,
    }


class SupportFundBody(BaseModel):
    support_fund: int


@router.patch("/claims/{claim_id}/support-fund", response_model=ClaimSummaryResponse)
async def update_support_fund(
    claim_id: UUID,
    body: SupportFundBody,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    claim = await db.get(Claim, claim_id)
    if not claim or claim.hospital_id != current_user.hospital_id:
        raise HTTPException(status_code=404, detail="청구를 찾을 수 없습니다.")
    claim.support_fund = body.support_fund
    await db.commit()
    await db.refresh(claim)

    items_result = await db.execute(
        select(ClaimLineItem)
        .where(ClaimLineItem.claim_id == claim.id)
        .options(selectinload(ClaimLineItem.acupoints))
    )
    all_items = items_result.scalars().all()
    year, month = claim.claim_period_year, claim.claim_period_month

    return ClaimSummaryResponse(
        id=str(claim.id),
        patient_id=str(claim.patient_id),
        billing_month=f"{year}-{month:02d}",
        status=claim.status,
        total_amount=claim.total_amount,
        line_items=[_line_item_to_response(i) for i in all_items],
    )
