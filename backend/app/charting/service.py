import json
import uuid as uuid_mod

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.charting.stt.chunker import transcribe_chunks
from app.diagnosis.claude_client import diagnose
from app.core.models import AIResult, MedicalRecord
from app.pipeline.deidentifier import deidentifier
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import select
from fastapi import HTTPException, status
from app.core.models import MedicalRecord, Patient, Doctor


async def create_medical_record(db, doctor, patient_id: UUID) -> MedicalRecord:

    result = await db.execute(
        select(Patient).where(
            Patient.id == patient_id, Patient.hospital_id == doctor.hospital_id
        )
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="등록된 회원이 아닙니다."
        )
    medical_record = MedicalRecord(
        patient_id=patient_id,
        doctor_id=doctor.id,
        hospital_id=doctor.hospital_id,
        status="recording",
        recorded_at=datetime.now(timezone.utc),
    )
    db.add(medical_record)
    await db.commit()
    await db.refresh(medical_record)
    return medical_record


async def update_record_status(db, record_id: UUID, new_status: str) -> MedicalRecord:
    result = await db.execute(
        select(MedicalRecord).where(MedicalRecord.id == record_id)
    )
    medical_record = result.scalar_one_or_none()
    if not medical_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="존재하지않는 의료기록입니다..",
        )
    medical_record.status = new_status
    await db.commit()
    await db.refresh()
    return medical_record


async def get_medical_record(
    db: AsyncSession, doctor: Doctor, record_id: UUID
) -> MedicalRecord:
    # doctor.hospital_id 스코프로 조회
    # 없으면 404
    result = await db.execute(
        select(MedicalRecord).where(
            MedicalRecord.id == record_id,
            MedicalRecord.hospital_id == doctor.hospital_id,
        )
    )
    medical_record = result.scalar_one_or_none()

    if not medical_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="존재하지않는 의료기록입니다..",
        )
    return medical_record


async def get_records_by_patient(
    db: AsyncSession, patient_id: UUID, doctor: Doctor
) -> list[MedicalRecord]:
    result = await db.execute(
        select(MedicalRecord)
        .where(
            MedicalRecord.patient_id == patient_id,
            MedicalRecord.hospital_id == doctor.hospital_id,
        )
        .order_by(MedicalRecord.created_at.desc())
    )
    medical_records = result.scalars().all()
    return medical_records


async def update_audio_url(db, record_id: UUID, audio_file_url: str) -> MedicalRecord:
    result = await db.execute(
        select(MedicalRecord).where(MedicalRecord.id == record_id)
    )
    medical_record = result.scalar_one_or_none()
    if not medical_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="존재하지않는 의료기록입니다..",
        )
    medical_record.audio_file_url = audio_file_url
    await db.commit()
    await db.refresh()
    return medical_record


async def process_chart(
    audio_file: UploadFile,
    patient_id: uuid_mod.UUID,
    doctor_id: uuid_mod.UUID,
    hospital_id: uuid_mod.UUID,
    db: AsyncSession,
) -> dict:
    # 1. STT
    audio_bytes = await audio_file.read()
    fmt = (audio_file.filename or "audio.mp3").rsplit(".", 1)[-1].lower()
    raw_text = await transcribe_chunks(audio_bytes, format=fmt)

    # 2. 비식별화 — 원본은 DB 저장, 마스킹본은 Claude로
    deid = deidentifier.process(raw_text)

    # 3. AI 진단
    diagnosis = diagnose(deid.cleaned)

    # 4. DB 저장
    record = MedicalRecord(
        patient_id=patient_id,
        doctor_id=doctor_id,
        hospital_id=hospital_id,
        raw_transcription=deid.original,
        chart_structured=deid.cleaned,
        status="completed",
    )
    db.add(record)
    await db.flush()

    ai_result = AIResult(
        medical_record_id=record.id,
        diagnosis_suggestion=json.dumps(diagnosis, ensure_ascii=False),
    )
    db.add(ai_result)
    await db.commit()
    await db.refresh(record)

    return {
        "record_id": record.id,
        "transcription": deid.cleaned,
        "diagnosis": diagnosis,
    }
