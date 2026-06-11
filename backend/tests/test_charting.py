import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.charting.service import finalize_record, process_chart
from app.core.models import AIResult, MedicalRecord

_SAMPLE_STT = "환자 홍길동 님 두통이 심합니다 연락처는 010-1234-5678입니다"
_SAMPLE_DIAGNOSIS = {"주호소": "두통", "진단": "간양항진증"}


class _FakeUploadFile:
    def __init__(self, content: bytes = b"audio", filename: str = "test.mp3"):
        self._content = content
        self.filename = filename

    async def read(self) -> bytes:
        return self._content


def _uuids():
    return uuid.uuid4(), uuid.uuid4(), uuid.uuid4()  # patient, doctor, hospital


async def test_정상_흐름_반환값_구조(db, monkeypatch):
    monkeypatch.setattr(
        "app.charting.service.transcribe_chunks", AsyncMock(return_value=_SAMPLE_STT)
    )
    monkeypatch.setattr(
        "app.charting.service.diagnose", AsyncMock(return_value=_SAMPLE_DIAGNOSIS)
    )

    patient_id, doctor_id, hospital_id = _uuids()
    result = await process_chart(
        audio_file=_FakeUploadFile(),
        patient_id=patient_id,
        doctor_id=doctor_id,
        hospital_id=hospital_id,
        db=db,
    )

    assert "record_id" in result
    assert "transcription" in result
    assert result["diagnosis"] == _SAMPLE_DIAGNOSIS


async def test_DB에_MedicalRecord_AIResult_저장됨(db, monkeypatch):
    monkeypatch.setattr(
        "app.charting.service.transcribe_chunks", AsyncMock(return_value=_SAMPLE_STT)
    )
    monkeypatch.setattr(
        "app.charting.service.diagnose", AsyncMock(return_value=_SAMPLE_DIAGNOSIS)
    )

    patient_id, doctor_id, hospital_id = _uuids()
    result = await process_chart(
        audio_file=_FakeUploadFile(),
        patient_id=patient_id,
        doctor_id=doctor_id,
        hospital_id=hospital_id,
        db=db,
    )

    record = (
        await db.execute(
            select(MedicalRecord).where(MedicalRecord.id == result["record_id"])
        )
    ).scalar_one()
    ai = (
        await db.execute(
            select(AIResult).where(AIResult.medical_record_id == result["record_id"])
        )
    ).scalar_one()

    assert record.status == "completed"
    assert record.patient_id == patient_id
    assert record.raw_transcription == _SAMPLE_STT  # 원본 STT 그대로 저장
    assert "홍길동" not in record.chart_structured  # chart에는 비식별화됨
    assert ai.diagnosis_suggestion is not None


async def test_비식별화_후_Claude_호출(db, monkeypatch):
    """diagnose()에 전달되는 텍스트에 원본 PII가 없어야 함"""
    monkeypatch.setattr(
        "app.charting.service.transcribe_chunks", AsyncMock(return_value=_SAMPLE_STT)
    )

    received = {}

    async def _mock_diagnose(text):
        received["text"] = text
        return _SAMPLE_DIAGNOSIS

    monkeypatch.setattr("app.charting.service.diagnose", _mock_diagnose)

    patient_id, doctor_id, hospital_id = _uuids()
    await process_chart(
        audio_file=_FakeUploadFile(),
        patient_id=patient_id,
        doctor_id=doctor_id,
        hospital_id=hospital_id,
        db=db,
    )

    assert "홍길동" not in received["text"]
    assert "010-1234-5678" not in received["text"]


async def test_symptom_text_추가시_진단_텍스트에_포함됨(db, monkeypatch):
    monkeypatch.setattr(
        "app.charting.service.transcribe_chunks", AsyncMock(return_value=_SAMPLE_STT)
    )

    received = {}

    async def _mock_diagnose(text):
        received["text"] = text
        return _SAMPLE_DIAGNOSIS

    monkeypatch.setattr("app.charting.service.diagnose", _mock_diagnose)

    patient_id, doctor_id, hospital_id = _uuids()
    await process_chart(
        audio_file=_FakeUploadFile(),
        patient_id=patient_id,
        doctor_id=doctor_id,
        hospital_id=hospital_id,
        db=db,
        symptom_text="추가로 어지럼증도 있음",
    )

    assert "어지럼증" in received["text"]


async def test_medical_history_저장됨(db, monkeypatch):
    monkeypatch.setattr(
        "app.charting.service.transcribe_chunks", AsyncMock(return_value=_SAMPLE_STT)
    )
    monkeypatch.setattr(
        "app.charting.service.diagnose", AsyncMock(return_value=_SAMPLE_DIAGNOSIS)
    )

    patient_id, doctor_id, hospital_id = _uuids()
    result = await process_chart(
        audio_file=_FakeUploadFile(),
        patient_id=patient_id,
        doctor_id=doctor_id,
        hospital_id=hospital_id,
        db=db,
        medical_history="고혈압 약 복용 중",
    )

    record = (
        await db.execute(
            select(MedicalRecord).where(MedicalRecord.id == result["record_id"])
        )
    ).scalar_one()

    assert record.medical_history == "고혈압 약 복용 중"


async def test_medical_history_진단_텍스트에_포함됨(db, monkeypatch):
    monkeypatch.setattr(
        "app.charting.service.transcribe_chunks", AsyncMock(return_value=_SAMPLE_STT)
    )

    received = {}

    async def _mock_diagnose(text):
        received["text"] = text
        return _SAMPLE_DIAGNOSIS

    monkeypatch.setattr("app.charting.service.diagnose", _mock_diagnose)

    patient_id, doctor_id, hospital_id = _uuids()
    await process_chart(
        audio_file=_FakeUploadFile(),
        patient_id=patient_id,
        doctor_id=doctor_id,
        hospital_id=hospital_id,
        db=db,
        medical_history="고혈압 약 복용 중",
    )

    assert "고혈압" in received["text"]


async def test_finalize_record_업데이트(db, monkeypatch):
    monkeypatch.setattr(
        "app.charting.service.transcribe_chunks", AsyncMock(return_value=_SAMPLE_STT)
    )
    monkeypatch.setattr(
        "app.charting.service.diagnose", AsyncMock(return_value=_SAMPLE_DIAGNOSIS)
    )

    patient_id, doctor_id, hospital_id = _uuids()
    result = await process_chart(
        audio_file=_FakeUploadFile(),
        patient_id=patient_id,
        doctor_id=doctor_id,
        hospital_id=hospital_id,
        db=db,
        medical_history="고혈압 약 복용 중",
    )
    record_id = result["record_id"]

    record_before = (
        await db.execute(select(MedicalRecord).where(MedicalRecord.id == record_id))
    ).scalar_one()
    assert record_before.recorded_at is None

    chart_text = "■ 결과 1\n▶ 사상체질\n태음인"
    updated = await finalize_record(db, record_id, chart_text)

    assert updated.chart_structured == chart_text
    assert updated.recorded_at is not None
    # 주소증(raw_transcription), 병력은 유지되어야 함
    assert updated.raw_transcription == _SAMPLE_STT
    assert updated.medical_history == "고혈압 약 복용 중"


async def test_finalize_record_selected_result_저장됨(db, monkeypatch):
    monkeypatch.setattr(
        "app.charting.service.transcribe_chunks", AsyncMock(return_value=_SAMPLE_STT)
    )
    monkeypatch.setattr(
        "app.charting.service.diagnose", AsyncMock(return_value=_SAMPLE_DIAGNOSIS)
    )

    patient_id, doctor_id, hospital_id = _uuids()
    result = await process_chart(
        audio_file=_FakeUploadFile(),
        patient_id=patient_id,
        doctor_id=doctor_id,
        hospital_id=hospital_id,
        db=db,
    )
    record_id = result["record_id"]

    chart_text = "■ 결과 1\n▶ 사상체질\n태음인"
    updated = await finalize_record(db, record_id, chart_text, selected_result="result1")

    assert updated.selected_result == "result1"


async def test_STT_오류_전파(db, monkeypatch):
    monkeypatch.setattr(
        "app.charting.service.transcribe_chunks",
        AsyncMock(side_effect=Exception("CLOVA API 오류")),
    )

    with pytest.raises(Exception, match="CLOVA API 오류"):
        await process_chart(
            audio_file=_FakeUploadFile(),
            patient_id=uuid.uuid4(),
            doctor_id=uuid.uuid4(),
            hospital_id=uuid.uuid4(),
            db=db,
        )


async def test_진단_실패시_502_예외_전파(db, monkeypatch):
    monkeypatch.setattr(
        "app.charting.service.transcribe_chunks", AsyncMock(return_value=_SAMPLE_STT)
    )

    async def _raise(text):
        raise HTTPException(
            status_code=502, detail="AI 진단 결과를 파싱할 수 없습니다."
        )

    monkeypatch.setattr("app.charting.service.diagnose", _raise)

    with pytest.raises(HTTPException) as exc_info:
        await process_chart(
            audio_file=_FakeUploadFile(),
            patient_id=uuid.uuid4(),
            doctor_id=uuid.uuid4(),
            hospital_id=uuid.uuid4(),
            db=db,
        )
    assert exc_info.value.status_code == 502
