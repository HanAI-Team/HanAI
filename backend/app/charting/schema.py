from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ChartingResponse(BaseModel):
    record_id: UUID
    transcription: str
    diagnosis: dict


class UpdateMedicalHistoryRequest(BaseModel):
    medical_history: Optional[str] = None


class UpdateKcdCodeRequest(BaseModel):
    kcd_code: Optional[str] = None
    secondary_kcd_codes: Optional[list[str]] = None


class FinalizeRecordRequest(BaseModel):
    chart_structured: str
    selected_result: Optional[str] = None


class MedicalRecordResponse(BaseModel):
    id: UUID
    patient_id: UUID
    doctor_id: UUID
    hospital_id: UUID
    raw_transcription: Optional[str] = None
    chart_structured: Optional[str] = None
    audio_file_url: Optional[str] = None
    status: str
    kcd_code: Optional[str] = None
    secondary_kcd_codes: Optional[list[str]] = None
    recorded_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ChangeLogItem(BaseModel):
    id: UUID
    patient_id: UUID
    patient_name: str
    doctor_id: UUID
    created_at: datetime
    updated_at: datetime


class ChangeLogListResponse(BaseModel):
    total: int
    page: int
    size: int
    items: list[ChangeLogItem]


class UpdateStatusRequest(BaseModel):
    status: str  # recording / transcribing / completed / failed


class UpdateAudioUrlRequest(BaseModel):
    audio_file_url: str




class PrescriptionCreateRequest(BaseModel):
    prescription_name: str
    ingredients: Optional[str] = None
    dosage: Optional[str] = None
    notes: Optional[str] = None
    # 청구용 신규 필드
    prescription_type: Optional[str] = None      # raw_herb/generic/fixed/custom
    adjustment_type: Optional[str] = None         # B/A/S
    formula_code: Optional[str] = None
    unit_price: Optional[int] = 0
    daily_dosage_ratio: Optional[Decimal] = Decimal("1.0")
    total_dosage_days: Optional[int] = 0
    species_count: Optional[int] = 0
    total_weight_g: Optional[Decimal] = Decimal("0")
    low_cost_substitute: Optional[bool] = False
    low_cost_surcharge: Optional[int] = 0
    dispensing_fee: Optional[int] = 0
    patient_birth_date: Optional[date] = None     # 소아 계산용


class PrescriptionResponse(BaseModel):
    id: UUID
    medical_record_id: UUID
    prescription_name: Optional[str] = None
    prescription_type: Optional[str] = None
    adjustment_type: Optional[str] = None
    formula_code: Optional[str] = None
    unit_price: Optional[int] = None
    daily_dosage_ratio: Optional[Decimal] = None
    total_dosage_days: Optional[int] = None
    total_dosage_price: Optional[int] = None
    species_count: Optional[int] = None
    total_weight_g: Optional[Decimal] = None
    low_cost_substitute: Optional[bool] = None
    low_cost_surcharge: Optional[int] = None
    dispensing_fee: Optional[int] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)




class ProcedureType(str, Enum):
    ACUPUNCTURE = "침술"
    CHUNA = "추나"
    CUPPING = "부항"
    MOXIBUSTION = "뜸"
    OTHER = "기타"

class ProcedureCreateRequest(BaseModel):
    procedure_type: ProcedureType
    fee_master_code: Optional[str] = None  # 심평원 행위코드 (fee_master.code FK)
    details: Optional[dict] = None         # {"points": ["LI4", "ST36"]}
    amount: Optional[int] = 0


class ProcedureResponse(BaseModel):
    id: UUID
    medical_record_id: UUID
    procedure_type: str
    fee_master_code: Optional[str] = None
    unit_price: Optional[float] = None
    details: Optional[dict] = None
    amount: Optional[int] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)