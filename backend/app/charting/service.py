import json
import uuid as uuid_mod

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.charting.stt.chunker import transcribe_chunks
from app.diagnosis.claude_client import diagnose, diagnose_stream
from app.core.models import AIResult, MedicalRecord
from app.pipeline.deidentifier import deidentifier
from app.pipeline.postprocessor import postprocessor
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
        recorded_at=datetime.utcnow(),
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
    await db.refresh(medical_record)
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
    return list(medical_records)


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
    await db.refresh(medical_record)
    return medical_record


async def process_chart(
    audio_files: list[UploadFile],
    patient_id: uuid_mod.UUID,
    doctor_id: uuid_mod.UUID,
    hospital_id: uuid_mod.UUID,
    db: AsyncSession,
    symptom_text: str | None = None,
    medical_history: str | None = None,
) -> dict:
    import time
    import logging

    logger = logging.getLogger(__name__)
    t = time.time()
    # 1. STT — 업로드 순서대로 변환 후 합산
    texts = []
    for i, audio_file in enumerate(audio_files):
        file_t = time.time()
        audio_bytes = await audio_file.read()
        fmt = (audio_file.filename or "audio.mp3").rsplit(".", 1)[-1].lower()
        texts.append(await transcribe_chunks(audio_bytes, format=fmt))
        logger.info(
            f"[PERF] STT ({i + 1}/{len(audio_files)}, {audio_file.filename}): "
            f"{time.time() - file_t:.2f}s"
        )
    raw_text = "\n\n".join(texts)
    logger.info(f"[PERF] STT 전체: {time.time() - t:.2f}s")
    # 2. 비식별화 — 원본은 DB 저장, 마스킹본은 Claude로
    t = time.time()
    deid = deidentifier.process(raw_text)
    logger.info(f"[PERF] 비식별화: {time.time() - t:.2f}s")

    # 3. 한의학 용어 후처리
    corrected_text = postprocessor.correct(deid.cleaned)

    # 3-1. 직접 입력한 증상 텍스트 추가
    if symptom_text and symptom_text.strip():
        corrected_text += f"\n\n[추가 증상 입력]\n{symptom_text.strip()}"

    # 3-2. 기존 병력 추가
    if medical_history and medical_history.strip():
        corrected_text += f"\n\n[기존 병력]\n{medical_history.strip()}"

    # 4. AI 진단
    t = time.time()
    diagnosis = await diagnose(corrected_text)
    logger.info(f"[PERF] AI 진단: {time.time() - t:.2f}s")

    # 5. DB 저장
    t = time.time()
    record = MedicalRecord(
        patient_id=patient_id,
        doctor_id=doctor_id,
        hospital_id=hospital_id,
        raw_transcription=deid.original,
        chart_structured=corrected_text,
        status="completed",
        medical_history=medical_history,
    )
    db.add(record)
    await db.flush()

    ai_result = AIResult(
        medical_record_id=record.id,
        diagnosis_suggestion=json.dumps(diagnosis, ensure_ascii=False),
    )
    db.add(ai_result)
    await db.commit()
    logger.info(f"[PERF] DB 저장: {time.time() - t:.2f}s")
    await db.refresh(record)

    return {
        "record_id": record.id,
        "transcription": corrected_text,
        "diagnosis": diagnosis,
    }


async def process_chart_stream(
    audio_files: list[UploadFile],
    patient_id: uuid_mod.UUID,
    doctor_id: uuid_mod.UUID,
    hospital_id: uuid_mod.UUID,
    db: AsyncSession,
    symptom_text: str | None = None,
    medical_history: str | None = None,
):
    """결과1(dataset_based), 결과2(claude_based)를 완료되는 대로 yield하는 스트리밍 버전."""
    import time
    import logging

    logger = logging.getLogger(__name__)
    t = time.time()
    # 1. STT — 업로드 순서대로 변환 후 합산
    texts = []
    for i, audio_file in enumerate(audio_files):
        file_t = time.time()
        audio_bytes = await audio_file.read()
        fmt = (audio_file.filename or "audio.mp3").rsplit(".", 1)[-1].lower()
        texts.append(await transcribe_chunks(audio_bytes, format=fmt))
        logger.info(
            f"[PERF] STT ({i + 1}/{len(audio_files)}, {audio_file.filename}): "
            f"{time.time() - file_t:.2f}s"
        )
    raw_text = "\n\n".join(texts)
    logger.info(f"[PERF] STT 전체: {time.time() - t:.2f}s")

    # 2. 비식별화 — 원본은 DB 저장, 마스킹본은 Claude로
    deid = deidentifier.process(raw_text)

    # 3. 한의학 용어 후처리
    corrected_text = postprocessor.correct(deid.cleaned)

    # 3-1. 직접 입력한 증상 텍스트 추가
    if symptom_text and symptom_text.strip():
        corrected_text += f"\n\n[추가 증상 입력]\n{symptom_text.strip()}"

    # 3-2. 기존 병력 추가
    if medical_history and medical_history.strip():
        corrected_text += f"\n\n[기존 병력]\n{medical_history.strip()}"

    yield {"type": "transcription", "transcription": corrected_text}

    # 4. AI 진단 — 결과1, 결과2를 완료되는 대로 전송
    t = time.time()
    diagnosis: dict = {}
    async for key, value in diagnose_stream(corrected_text):
        diagnosis[key] = value
        logger.info(f"[PERF] AI 진단 ({key}): {time.time() - t:.2f}s")
        yield {"type": key, "data": value}

    # 5. DB 저장
    t = time.time()
    record = MedicalRecord(
        patient_id=patient_id,
        doctor_id=doctor_id,
        hospital_id=hospital_id,
        raw_transcription=deid.original,
        chart_structured=corrected_text,
        status="completed",
        medical_history=medical_history,
    )
    db.add(record)
    await db.flush()

    ai_result = AIResult(
        medical_record_id=record.id,
        diagnosis_suggestion=json.dumps(diagnosis, ensure_ascii=False),
    )
    db.add(ai_result)
    await db.commit()
    logger.info(f"[PERF] DB 저장: {time.time() - t:.2f}s")
    await db.refresh(record)

    yield {"type": "done", "record_id": str(record.id)}


async def update_medical_history(
    db: AsyncSession, record_id: UUID, medical_history: str | None
) -> MedicalRecord:
    result = await db.execute(
        select(MedicalRecord).where(MedicalRecord.id == record_id)
    )
    medical_record = result.scalar_one_or_none()
    if not medical_record:
        raise HTTPException(status_code=404, detail="진료 기록을 찾을 수 없습니다.")
    medical_record.medical_history = medical_history  # type: ignore
    await db.commit()
    await db.refresh(medical_record)
    return medical_record


async def finalize_record(
    db: AsyncSession,
    record_id: UUID,
    chart_structured: str,
    selected_result: str | None = None,
) -> MedicalRecord:
    result = await db.execute(
        select(MedicalRecord).where(MedicalRecord.id == record_id)
    )
    medical_record = result.scalar_one_or_none()
    if not medical_record:
        raise HTTPException(status_code=404, detail="진료 기록을 찾을 수 없습니다.")
    medical_record.chart_structured = chart_structured  # type: ignore
    medical_record.recorded_at = datetime.now(timezone.utc)  # type: ignore
    medical_record.selected_result = selected_result  # type: ignore
    await db.commit()
    await db.refresh(medical_record)
    return medical_record
