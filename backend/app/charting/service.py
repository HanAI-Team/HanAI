import json
import uuid as uuid_mod

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.charting.stt.chunker import transcribe_chunks
from app.diagnosis.claude_client import diagnose
from app.core.models import AIResult, MedicalRecord
from app.pipeline.deidentifier import deidentifier
from app.pipeline.postprocessor import postprocessor


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

    # 3. 한의학 용어 후처리 ← 추가
    corrected_text = postprocessor.correct(deid.cleaned)

    # 4. AI 진단
    diagnosis = diagnose(corrected_text)

    # 5. DB 저장
    record = MedicalRecord(
        patient_id=patient_id,
        doctor_id=doctor_id,
        hospital_id=hospital_id,
        raw_transcription=deid.original,
        chart_structured=corrected_text,
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
        "transcription": corrected_text,
        "diagnosis": diagnosis,
    }
