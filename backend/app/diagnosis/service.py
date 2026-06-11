import json
import uuid as uuid_mod
from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import AIResult, MedicalRecord
from app.diagnosis.claude_client import ask, diagnose


def run_ask(question: str) -> str:
    return ask(question)


def run_diagnosis(transcription: str) -> dict:
    return diagnose(transcription)


def _format_diagnosis_block(diagnosis: dict, label: str) -> str:
    constitution = (diagnosis.get("sasang_constitution") or {}).get("type", "-")
    tkm = (diagnosis.get("tkm_diagnosis") or {}).get("diagnosis_name", "-")
    western_name = (diagnosis.get("western_diagnosis") or {}).get("name", "-")
    herb = diagnosis.get("herbal_prescription") or {}
    herb_name = herb.get("name_kr", "-")
    composition = herb.get("composition") or []
    herb_str = ", ".join(
        f"{c.get('herb', '')} {c.get('dosage', '')}".strip()
        for c in composition
        if c.get("herb")
    )
    acu_list = diagnosis.get("acupuncture_prescription") or []
    acu_str = ", ".join(
        f"{p.get('point_kr', '')}({p.get('point_code', '')})"
        for p in acu_list
        if p.get("point_kr")
    )
    return (
        f"■ {label}\n"
        f"▶ 사상체질\n{constitution}\n\n"
        f"▶ 한의학적 진단\n{tkm}\n양방 대응: {western_name}\n\n"
        f"▶ 한약 처방\n{herb_name}\n{herb_str}\n\n"
        f"▶ 침 처방\n{acu_str}"
    )


def _format_chart_structured(diagnosis: dict) -> str:
    dataset_part = _format_diagnosis_block(
        diagnosis.get("dataset_based") or {}, "결과 1"
    )
    claude_part = _format_diagnosis_block(diagnosis.get("claude_based") or {}, "결과 2")
    return f"{dataset_part}\n\n{claude_part}"


async def save_text_diagnosis(
    db: AsyncSession,
    doctor,
    patient_id: UUID,
    transcription: str,
    diagnosis: dict,
) -> None:
    record = MedicalRecord(
        patient_id=patient_id,
        doctor_id=doctor.id,
        hospital_id=doctor.hospital_id,
        raw_transcription=transcription,
        chart_structured=_format_chart_structured(diagnosis),
        status="completed",
        recorded_at=datetime.utcnow(),
    )
    db.add(record)
    await db.flush()
    db.add(
        AIResult(
            medical_record_id=record.id,
            diagnosis_suggestion=json.dumps(diagnosis, ensure_ascii=False),
        )
    )
    await db.commit()


async def run_diagnosis_for_record(record_id: uuid_mod.UUID, db: AsyncSession) -> dict:
    result = await db.execute(
        select(MedicalRecord).where(MedicalRecord.id == record_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="MedicalRecord not found")
    if not record.chart_structured:
        raise HTTPException(status_code=400, detail="chart_structured is empty")

    diagnosis = await diagnose(record.chart_structured)
    print(diagnosis)
    primary = diagnosis.get("dataset_based") or {}
    existing = await db.execute(
        select(AIResult).where(AIResult.medical_record_id == record_id)
    )
    ai_result = existing.scalar_one_or_none()

    if ai_result:
        ai_result.diagnosis_suggestion = json.dumps(
            primary.get("tkm_diagnosis"), ensure_ascii=False
        )
        ai_result.constitution_result = json.dumps(
            primary.get("sasang_constitution"), ensure_ascii=False
        )
        ai_result.prescription_suggestion = json.dumps(
            primary.get("herbal_prescription"), ensure_ascii=False
        )
        ai_result.acupuncture_suggestion = json.dumps(
            primary.get("acupuncture_prescription"), ensure_ascii=False
        )
        ai_result.reasoning = diagnosis
    else:
        ai_result = AIResult(
            medical_record_id=record_id,
            diagnosis_suggestion=json.dumps(
                primary.get("tkm_diagnosis"), ensure_ascii=False
            ),
            constitution_result=json.dumps(
                primary.get("sasang_constitution"), ensure_ascii=False
            ),
            prescription_suggestion=json.dumps(
                primary.get("herbal_prescription"), ensure_ascii=False
            ),
            acupuncture_suggestion=json.dumps(
                primary.get("acupuncture_prescription"), ensure_ascii=False
            ),
            reasoning=diagnosis,
        )
        db.add(ai_result)

    await db.commit()
    return {"record_id": record_id, "diagnosis": diagnosis}


async def get_diagnosis_result(record_id: uuid_mod.UUID, db: AsyncSession) -> dict:
    result = await db.execute(
        select(AIResult).where(AIResult.medical_record_id == record_id)
    )
    ai_result = result.scalar_one_or_none()
    if not ai_result:
        raise HTTPException(status_code=404, detail="Diagnosis result not found")

    return {"record_id": record_id, "diagnosis": ai_result.reasoning}
