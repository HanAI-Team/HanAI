import uuid as uuid_mod

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.charting.stt.client import clova_client
from app.diagnosis.claude_client import diagnose
from app.core.models import AIResult, MedicalRecord
from app.pipeline.deidentifier import deidentifier


async def process_chart(
    audio_file: UploadFile,
    patient_id: uuid_mod.UUID,
    doctor_id: uuid_mod.UUID,
    hospital_id: uuid_mod.UUID,
    db: AsyncSession,
) -> dict:
    # 1. STT
    audio_bytes = await audio_file.read()
    raw_text = await clova_client.transcribe(audio_bytes)

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
        diagnosis_suggestion=diagnosis,
    )
    db.add(ai_result)
    await db.commit()
    await db.refresh(record)

    return {
        "record_id": record.id,
        "transcription": deid.cleaned,
        "diagnosis": diagnosis,
    }
