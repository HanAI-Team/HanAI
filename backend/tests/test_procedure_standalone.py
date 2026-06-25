import uuid
from types import SimpleNamespace

import pytest
import pytest_asyncio
from fastapi import HTTPException

from app.charting.procedure_service import add_procedure
from app.charting.schema import ProcedureCreateRequest, ProcedureType
from app.core.models import FeeMaster, MedicalRecord


@pytest_asyncio.fixture
async def fee_codes(db):
    """일반침술/분구침술 테스트용 fee_master 행위코드."""
    normal = FeeMaster(
        code="TEST-NORMAL",
        name="일반침술",
        category="침술",
        unit_price=1000,
        is_standalone=False,
    )
    standalone = FeeMaster(
        code="TEST-STANDALONE",
        name="분구침술",
        category="분구침술",
        unit_price=0,
        is_standalone=True,
    )
    db.add_all([normal, standalone])
    await db.commit()
    return normal, standalone


@pytest_asyncio.fixture
async def medical_record(db):
    hospital_id = uuid.uuid4()
    record = MedicalRecord(
        patient_id=uuid.uuid4(),
        doctor_id=uuid.uuid4(),
        hospital_id=hospital_id,
        status="completed",
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    doctor = SimpleNamespace(id=record.doctor_id, hospital_id=hospital_id)
    return record, doctor


async def test_분구침술_추가시_일반침술_있으면_400(db, fee_codes, medical_record):
    normal, standalone = fee_codes
    record, doctor = medical_record

    await add_procedure(
        db,
        doctor,
        record.id,
        ProcedureCreateRequest(
            procedure_type=ProcedureType.ACUPUNCTURE, fee_master_code=normal.code
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        await add_procedure(
            db,
            doctor,
            record.id,
            ProcedureCreateRequest(
                procedure_type=ProcedureType.ACUPUNCTURE, fee_master_code=standalone.code
            ),
        )
    assert exc_info.value.status_code == 400


async def test_일반침술_추가시_분구침술_있으면_400(db, fee_codes, medical_record):
    normal, standalone = fee_codes
    record, doctor = medical_record

    await add_procedure(
        db,
        doctor,
        record.id,
        ProcedureCreateRequest(
            procedure_type=ProcedureType.ACUPUNCTURE, fee_master_code=standalone.code
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        await add_procedure(
            db,
            doctor,
            record.id,
            ProcedureCreateRequest(
                procedure_type=ProcedureType.ACUPUNCTURE, fee_master_code=normal.code
            ),
        )
    assert exc_info.value.status_code == 400


async def test_분구침술만_단독_추가는_성공(db, fee_codes, medical_record):
    normal, standalone = fee_codes
    record, doctor = medical_record

    procedure = await add_procedure(
        db,
        doctor,
        record.id,
        ProcedureCreateRequest(
            procedure_type=ProcedureType.ACUPUNCTURE, fee_master_code=standalone.code
        ),
    )
    assert procedure.fee_master_code == standalone.code


async def test_일반침술만_단독_추가는_성공(db, fee_codes, medical_record):
    normal, standalone = fee_codes
    record, doctor = medical_record

    procedure = await add_procedure(
        db,
        doctor,
        record.id,
        ProcedureCreateRequest(
            procedure_type=ProcedureType.ACUPUNCTURE, fee_master_code=normal.code
        ),
    )
    assert procedure.fee_master_code == normal.code
