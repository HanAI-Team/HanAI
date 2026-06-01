import json
import uuid as uuid_mod

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import AIResult, MedicalRecord
from app.diagnosis.claude_client import ask, diagnose


def run_ask(question: str) -> str:
    return ask(question)


def run_diagnosis(transcription: str) -> dict:
    return diagnose(transcription)


async def run_diagnosis_for_record(record_id: uuid_mod.UUID, db: AsyncSession) -> dict:
    result = await db.execute(
        select(MedicalRecord).where(MedicalRecord.id == record_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="MedicalRecord not found")
    if not record.chart_structured:
        raise HTTPException(status_code=400, detail="chart_structured is empty")

    diagnosis = diagnose(record.chart_structured)
    print(diagnosis)
    existing = await db.execute(
        select(AIResult).where(AIResult.medical_record_id == record_id)
    )
    ai_result = existing.scalar_one_or_none()

    if ai_result:
        ai_result.diagnosis_suggestion = json.dumps(
            diagnosis.get("tkm_diagnosis"), ensure_ascii=False
        )
        ai_result.constitution_result = json.dumps(
            diagnosis.get("sasang_constitution"), ensure_ascii=False
        )
        ai_result.prescription_suggestion = json.dumps(
            diagnosis.get("herbal_prescription"), ensure_ascii=False
        )
        ai_result.acupuncture_suggestion = json.dumps(
            diagnosis.get("acupuncture_prescription"), ensure_ascii=False
        )
        ai_result.reasoning = diagnosis
    else:
        ai_result = AIResult(
            medical_record_id=record_id,
            diagnosis_suggestion=json.dumps(
                diagnosis.get("tkm_diagnosis"), ensure_ascii=False
            ),
            constitution_result=json.dumps(
                diagnosis.get("sasang_constitution"), ensure_ascii=False
            ),
            prescription_suggestion=json.dumps(
                diagnosis.get("herbal_prescription"), ensure_ascii=False
            ),
            acupuncture_suggestion=json.dumps(
                diagnosis.get("acupuncture_prescription"), ensure_ascii=False
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
