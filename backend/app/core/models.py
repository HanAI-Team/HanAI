import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Date,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Hospital(Base):
    __tablename__ = "hospitals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    address = Column(String)
    phone = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    doctors = relationship("Doctor", back_populates="hospital")
    staff_accounts = relationship("StaffAccount", back_populates="hospital")
    patients = relationship("Patient", back_populates="hospital")
    medical_records = relationship("MedicalRecord", back_populates="hospital")
    subscription = relationship(
        "Subscription", back_populates="hospital", uselist=False
    )


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
    hospital_id = Column(
        UUID(as_uuid=True), ForeignKey("hospitals.id"), unique=True, nullable=False
    )
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
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    hospital = relationship("Hospital", back_populates="patients")
    medical_records = relationship("MedicalRecord", back_populates="patient")


class MedicalRecord(Base):
    __tablename__ = "medical_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctors.id"), nullable=False)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey("hospitals.id"), nullable=False)
    raw_transcription = Column(Text)
    chart_structured = Column(Text)
    audio_file_url = Column(String)
    status = Column(String, default="recording")
    recorded_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    medical_history = Column(Text, nullable=True)
    selected_result = Column(String, nullable=True)

    patient = relationship("Patient", back_populates="medical_records")
    doctor = relationship("Doctor", back_populates="medical_records")
    hospital = relationship("Hospital", back_populates="medical_records")
    ai_result = relationship(
        "AIResult",
        back_populates="medical_record",
        uselist=False,
        cascade="all, delete-orphan",
    )
    prescriptions = relationship(
        "Prescription", back_populates="medical_record", cascade="all, delete-orphan"
    )


class AIResult(Base):
    __tablename__ = "ai_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    medical_record_id = Column(
        UUID(as_uuid=True),
        ForeignKey("medical_records.id"),
        unique=True,
        nullable=False,
    )
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
    ai_result_id = Column(
        UUID(as_uuid=True), ForeignKey("ai_results.id"), nullable=False
    )
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctors.id"), nullable=False)
    category = Column(String)
    score = Column(Integer)
    comment = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ai_result = relationship(
        "AIResult",
        back_populates="feedbacks",
        uselist=False,
    )
    doctor = relationship("Doctor", back_populates="feedbacks")


class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    medical_record_id = Column(
        UUID(as_uuid=True), ForeignKey("medical_records.id"), nullable=False
    )
    prescription_name = Column(String)
    ingredients = Column(Text)
    dosage = Column(String)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    medical_record = relationship("MedicalRecord", back_populates="prescriptions")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    table_name = Column(String(50), nullable=False)
    record_id = Column(String(36), nullable=False)
    action = Column(String(10), nullable=False)  # INSERT / UPDATE / DELETE
    actor_id = Column(UUID(as_uuid=True), nullable=True)
    actor_type = Column(String(20), nullable=True)  # doctor / staff
    changed_at = Column(String(14), nullable=False)  # CCYYMMDDHHMMSS
    detail = Column(Text, nullable=True)


class AcupuncturePoint(Base):
    __tablename__ = "acupuncture_points"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True, nullable=False, index=True)
    korean_name = Column(String(50), nullable=False)
    meridian = Column(String(30), nullable=True)
    location = Column(Text, nullable=True)
    # True면 해당 회차에 다른 단독침술과 동시 청구 불가
    is_standalone = Column(Boolean, default=False, nullable=False)


class KcdUCode(Base):
    __tablename__ = "kcd_u_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    korean_name = Column(String(100), nullable=False)
    hanja = Column(String(100))
    category = Column(String(100))
    effective_date = Column(Date, nullable=True)
    expired_date = Column(Date, nullable=True)
