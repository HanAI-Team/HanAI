import uuid

from app.core.crypto import EncryptedString
from app.core.database import Base
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


class Hospital(Base):
    __tablename__ = "hospitals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    address = Column(String)
    phone = Column(String)
    institution_code = Column(String(8), nullable=True)  # 심평원 요양기관기호
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    doctors = relationship("Doctor", back_populates="hospital")
    staff_accounts = relationship("StaffAccount", back_populates="hospital")
    patients = relationship("Patient", back_populates="hospital")
    medical_records = relationship("MedicalRecord", back_populates="hospital")
    subscription = relationship("Subscription", back_populates="hospital", uselist=False)
    

class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey("hospitals.id"), nullable=False)
    name = Column(String, nullable=False)
    license_number = Column(String, unique=True, nullable=False)
    license_kind = Column(String)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="owner")
    is_approved = Column(Boolean, default=False, nullable=False)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    license_verified_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    hospital = relationship("Hospital", back_populates="doctors")
    medical_records = relationship("MedicalRecord", back_populates="doctor")
    feedbacks = relationship("Feedback", back_populates="doctor")


class StaffAccount(Base):
    __tablename__ = "staff_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey("hospitals.id"), nullable=False)
    name = Column(String, nullable=False)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="nurse")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    hospital = relationship("Hospital", back_populates="staff_accounts")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey("hospitals.id"), unique=True, nullable=False)
    tier = Column(String, default="basic")
    status = Column(String, default="active")
    staff_limit = Column(Integer, default=2)
    started_at = Column(DateTime(timezone=True))
    expired_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    hospital = relationship("Hospital", back_populates="subscription")


class Patient(Base):
    __tablename__ = "patients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey("hospitals.id"), nullable=False)
    name = Column(String, nullable=False)
    birth_date = Column(Date)
    gender = Column(String)
    phone = Column(String)
    memo = Column(Text)
    insurance_type = Column(String, default="health")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    hospital = relationship("Hospital", back_populates="patients")
    medical_records = relationship("MedicalRecord", back_populates="patient")
    rrn = Column(EncryptedString(500), nullable=True)


class Claim(Base):
    __tablename__ = "claims"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctors.id"), nullable=False)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey("hospitals.id"), nullable=False)
    claim_period_year = Column(Integer, nullable=False)
    claim_period_month = Column(Integer, nullable=False)
    claim_type = Column(String, nullable=True)
    total_amount = Column(Integer, nullable=False, default=0)
    patient_copay = Column(Integer, nullable=False, default=0)
    claim_amount = Column(Integer, nullable=False, default=0)
    differential_index = Column(Numeric(5, 2), default=1.0)
    status = Column(String, nullable=False, default="draft")
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    medical_records = relationship("MedicalRecord", back_populates="claim")
    line_items = relationship("ClaimLineItem", back_populates="claim", cascade="all, delete-orphan")


class ClaimLineItem(Base):
    """차트 화면에서 항목 클릭 시 생성되는 청구 라인. EDI C2-71과 1:1 대응."""

    __tablename__ = "claim_line_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_id = Column(UUID(as_uuid=True), ForeignKey("claims.id"), nullable=False)
    medical_record_id = Column(UUID(as_uuid=True), ForeignKey("medical_records.id"), nullable=False)

    hang = Column(String(2), nullable=False)
    mok = Column(String(2), nullable=False)
    code = Column(String(9), nullable=False)
    name = Column(String(50), nullable=False)

    unit_price = Column(Numeric(10, 2), nullable=False, default=0)
    qty = Column(Numeric(5, 2), nullable=False, default=1)
    days = Column(Integer, nullable=False, default=1)
    amount = Column(Integer, nullable=False, default=0)

    hyeolmyeong_names = Column(JSON, nullable=True)  # 침술일 때 경혈명 목록

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    claim = relationship("Claim", back_populates="line_items")


class MedicalRecord(Base):
    __tablename__ = "medical_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctors.id"), nullable=False)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey("hospitals.id"), nullable=False)
    claim_id = Column(UUID(as_uuid=True), ForeignKey("claims.id"), nullable=True)
    raw_transcription = Column(Text)
    chart_structured = Column(Text)
    audio_file_url = Column(String)
    status = Column(String, default="recording")
    kcd_code = Column(String(10), nullable=True)  # KCD 상병코드 (EDI C2-02)
    recorded_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    medical_history = Column(Text, nullable=True)
    selected_result = Column(String, nullable=True)

    patient = relationship("Patient", back_populates="medical_records")
    doctor = relationship("Doctor", back_populates="medical_records")
    hospital = relationship("Hospital", back_populates="medical_records")
    claim = relationship("Claim", back_populates="medical_records")
    ai_result = relationship("AIResult", back_populates="medical_record", uselist=False, cascade="all, delete-orphan")
    prescriptions = relationship("Prescription", back_populates="medical_record", cascade="all, delete-orphan")
    procedures = relationship("MedicalRecordProcedure", back_populates="medical_record", cascade="all, delete-orphan")


class AIResult(Base):
    __tablename__ = "ai_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    medical_record_id = Column(UUID(as_uuid=True), ForeignKey("medical_records.id"), unique=True, nullable=False)
    diagnosis_suggestion = Column(Text)
    constitution_result = Column(Text)
    prescription_suggestion = Column(Text)
    acupuncture_suggestion = Column(Text)
    reasoning = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    medical_record = relationship("MedicalRecord", back_populates="ai_result")
    feedbacks = relationship("Feedback", back_populates="ai_result")


class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ai_result_id = Column(UUID(as_uuid=True), ForeignKey("ai_results.id"), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctors.id"), nullable=False)
    category = Column(String)
    score = Column(Integer)
    comment = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ai_result = relationship("AIResult", back_populates="feedbacks", uselist=False)
    doctor = relationship("Doctor", back_populates="feedbacks")


class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    medical_record_id = Column(UUID(as_uuid=True), ForeignKey("medical_records.id"), nullable=False)
    prescription_name = Column(String)
    ingredients = Column(Text)
    dosage = Column(String)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    prescription_type = Column(String, nullable=True)
    adjustment_type = Column(String, nullable=True)
    formula_code = Column(String, nullable=True)
    unit_price = Column(Integer, default=0)
    daily_dosage_ratio = Column(Numeric(4, 2), default=1.0)
    total_dosage_days = Column(Integer, default=0)
    total_dosage_price = Column(Integer, default=0)
    species_count = Column(Integer, default=0)
    total_weight_g = Column(Numeric(8, 2), default=0)
    low_cost_substitute = Column(Boolean, default=False)
    low_cost_surcharge = Column(Integer, default=0)
    dispensing_fee = Column(Integer, default=0)

    medical_record = relationship("MedicalRecord", back_populates="prescriptions")


class MedicalRecordProcedure(Base):
    __tablename__ = "medical_record_procedures"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    medical_record_id = Column(UUID(as_uuid=True), ForeignKey("medical_records.id", ondelete="CASCADE"), nullable=False)
    procedure_type = Column(String, nullable=False)
    details = Column(JSON, nullable=True)
    amount = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # EDI 명세서진료내역 필수 필드
    hang          = Column(String(2),  nullable=True)               # 항번호 (04=시술및처치료)
    mok           = Column(String(2),  nullable=True)               # 목번호 (01=침술 02=구술 03=부항 04=처치 99=기타)
    code_gubun    = Column(String(1),  nullable=True, default="A")  # 코드구분 (A=수가 B=전용 C=약가 H=치료재료)
    unit_price    = Column(Numeric(12, 2), nullable=True)           # 단가
    qty           = Column(Numeric(7, 2),  nullable=True)           # 1일투여량/실시횟수
    days          = Column(Integer,    nullable=True)               # 총투여일수/실시횟수
    license_type  = Column(String(1),  nullable=True, default="3") # 면허종류 (3=한의사)
    license_no    = Column(String(10), nullable=True)              # 면허번호
    special_detail = Column(String(700), nullable=True)            # 특정내역 (JS011 혈명코드 등)
    fee_master_code = Column(String(20), ForeignKey("fee_master.code"), nullable=True)

    # C2-13 명세서진료내역(의치과및한방) 필드
    prescription_days = Column(Integer, default=0, nullable=True)           # 처방일수
    copay_rate_code = Column(String(2), default="D", nullable=True)         # 본인부담률구분코드
    prescription_issue_date = Column(String(8), nullable=True)              # 처방전발급일자
    prescription_serial = Column(Integer, default=0, nullable=True)         # 처방전일련번호
    adjustment_type = Column(String(10), nullable=True)                     # 가감등구분

    medical_record = relationship("MedicalRecord", back_populates="procedures")
    fee_master = relationship("FeeMaster", foreign_keys="[MedicalRecordProcedure.fee_master_code]")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    table_name = Column(String(50), nullable=False)
    record_id = Column(String(36), nullable=False)
    action = Column(String(10), nullable=False)
    actor_id = Column(UUID(as_uuid=True), nullable=True)
    actor_type = Column(String(20), nullable=True)
    changed_at = Column(String(14), nullable=False)
    detail = Column(Text, nullable=True)


class AcupuncturePoint(Base):
    __tablename__ = "acupuncture_points"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True, nullable=False, index=True)
    korean_name = Column(String(50), nullable=False)
    meridian = Column(String(30), nullable=True)
    location = Column(Text, nullable=True)
    is_standalone = Column(Boolean, default=False, nullable=False)
    forbidden_with = Column(JSON, nullable=True)


class KcdUCode(Base):
    __tablename__ = "kcd_u_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    korean_name = Column(String(100), nullable=False)
    hanja = Column(String(100))
    category = Column(String(100))
    effective_date = Column(Date, nullable=True)
    expired_date = Column(Date, nullable=True)
    sex_restriction = Column(String(1), nullable=True)  # M=남성, F=여성, None=제한없음
    is_notifiable = Column(Boolean, default=False)       # 법정감염병 여부
class FeeMaster(Base):
    """한방 행위코드 수가 마스터 (HIRA 요양급여비용 목록표 기준)."""

    __tablename__ = "fee_master"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False, index=True)   # 행위코드
    name = Column(String(100), nullable=False)                            # 행위명
    category = Column(String(20), nullable=False)                         # 침술/뜸/부항/추나
    insured_health      = Column(Boolean, nullable=False, server_default="true")   # 건강보험(4) 적용 여부
    insured_medical_aid = Column(Boolean, nullable=False, server_default="true")   # 의료급여(5) 적용 여부
    insured_veterans    = Column(Boolean, nullable=False, server_default="false")  # 보훈(7) 적용 여부
    unit_price = Column(Integer, nullable=False)                          # 수가 (원, 건강보험 기준)
    is_insured = Column(Boolean, default=True, nullable=False)            # 급여 여부
    effective_date = Column(Date, nullable=True)
    expired_date = Column(Date, nullable=True)
    is_standalone = Column(Boolean, default=False, nullable=False, server_default="false")
