import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
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
    created_at = Column(DateTime, server_default=func.now())

    doctors = relationship("Doctor", back_populates="hospital")
    patients = relationship("Patient", back_populates="hospital")
    medical_records = relationship("MedicalRecord", back_populates="hospital")


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey("hospitals.id"), nullable=False)
    name = Column(String, nullable=False)
    license_number = Column(String, unique=True, nullable=False)
    license_kind = Column(String)
    license_verified_at = Column(DateTime)
    is_approved = Column(Boolean, default=False, nullable=False)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    hospital = relationship("Hospital", back_populates="doctors")
    subscription = relationship("Subscription", back_populates="doctor", uselist=False)
    medical_records = relationship("MedicalRecord", back_populates="doctor")
    feedbacks = relationship("Feedback", back_populates="doctor")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doctor_id = Column(
        UUID(as_uuid=True), ForeignKey("doctors.id"), unique=True, nullable=False
    )
    tier = Column(String, default="basic")
    status = Column(String, default="active")
    started_at = Column(DateTime)
    expired_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

    doctor = relationship("Doctor", back_populates="subscription")


class Patient(Base):
    __tablename__ = "patients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey("hospitals.id"), nullable=False)
    name = Column(String, nullable=False)
    birth_date = Column(Date)
    gender = Column(String)
    phone = Column(String)
    memo = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

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
    recorded_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

    patient = relationship("Patient", back_populates="medical_records")
    doctor = relationship("Doctor", back_populates="medical_records")
    hospital = relationship("Hospital", back_populates="medical_records")
    ai_result = relationship("AIResult", back_populates="medical_record", uselist=False)
    prescriptions = relationship("Prescription", back_populates="medical_record")


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
    created_at = Column(DateTime, server_default=func.now())

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
    created_at = Column(DateTime, server_default=func.now())

    ai_result = relationship("AIResult", back_populates="feedbacks")
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
    created_at = Column(DateTime, server_default=func.now())

    medical_record = relationship("MedicalRecord", back_populates="prescriptions")
