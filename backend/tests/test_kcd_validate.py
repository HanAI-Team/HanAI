import logging
import pytest
from datetime import date

pytestmark = pytest.mark.asyncio


async def test_validate_유효한_단일코드(client, approved_doctor, kcd_codes):
    _, headers = approved_doctor
    res = await client.post("/api/kcd/validate", json={"codes": ["A001"]}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["has_error"] is False
    assert data["results"][0]["is_valid"] is True
    assert data["results"][0]["korean_name"] == "콜레라"


async def test_validate_존재하지않는_코드(client, approved_doctor, kcd_codes):
    _, headers = approved_doctor
    res = await client.post("/api/kcd/validate", json={"codes": ["X999"]}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["has_error"] is True
    assert data["results"][0]["is_valid"] is False
    assert "존재하지 않는 상병코드" in data["results"][0]["error"]


async def test_validate_복수코드_혼합(client, approved_doctor, kcd_codes):
    _, headers = approved_doctor
    res = await client.post("/api/kcd/validate", json={"codes": ["A001", "X999"]}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["has_error"] is True
    valid = next(r for r in data["results"] if r["code"] == "A001")
    invalid = next(r for r in data["results"] if r["code"] == "X999")
    assert valid["is_valid"] is True
    assert invalid["is_valid"] is False


async def test_validate_전부_유효(client, approved_doctor, kcd_codes):
    _, headers = approved_doctor
    res = await client.post("/api/kcd/validate", json={"codes": ["A001", "B001"]}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["has_error"] is False
    assert all(r["is_valid"] for r in data["results"])


async def test_validate_소문자_입력_대문자로_정규화(client, approved_doctor, kcd_codes):
    _, headers = approved_doctor
    res = await client.post("/api/kcd/validate", json={"codes": ["a001"]}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["results"][0]["is_valid"] is True
    assert data["results"][0]["code"] == "A001"


async def test_validate_공백포함_코드_정규화(client, approved_doctor, kcd_codes):
    _, headers = approved_doctor
    res = await client.post("/api/kcd/validate", json={"codes": [" A001 "]}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["results"][0]["is_valid"] is True
    assert data["results"][0]["code"] == "A001"


async def test_validate_빈_목록(client, approved_doctor, kcd_codes):
    _, headers = approved_doctor
    res = await client.post("/api/kcd/validate", json={"codes": []}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["results"] == []
    assert data["has_error"] is False


async def test_validate_만료된_코드(client, approved_doctor, kcd_codes):
    _, headers = approved_doctor
    res = await client.post("/api/kcd/validate", json={"codes": ["Z999"]}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["has_error"] is True
    assert data["results"][0]["is_valid"] is False
    assert "유효기간이 만료된 상병코드" in data["results"][0]["error"]


async def test_validate_as_of_미래날짜(client, approved_doctor, kcd_codes):
    """as_of를 미래 날짜로 보내도 유효한 코드는 통과해야 함."""
    _, headers = approved_doctor
    res = await client.post(
        "/api/kcd/validate",
        json={"codes": ["A001"], "as_of": "2099-01-01"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["results"][0]["is_valid"] is True


async def test_validate_인증없으면_401(client, kcd_codes):
    res = await client.post("/api/kcd/validate", json={"codes": ["A001"]})
    assert res.status_code == 401


async def test_validate_남성전용코드_여성환자_불일치(client, approved_doctor, kcd_codes):
    _, headers = approved_doctor
    res = await client.post(
        "/api/kcd/validate",
        json={"codes": ["M001"], "patient_gender": "F"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["has_error"] is True
    assert data["results"][0]["is_valid"] is False
    assert "남성 전용 상병코드" in data["results"][0]["error"]


async def test_validate_남성전용코드_남성환자_일치(client, approved_doctor, kcd_codes):
    _, headers = approved_doctor
    res = await client.post(
        "/api/kcd/validate",
        json={"codes": ["M001"], "patient_gender": "M"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["has_error"] is False
    assert data["results"][0]["is_valid"] is True


async def test_validate_법정감염병_is_notifiable_반환(client, approved_doctor, kcd_codes):
    _, headers = approved_doctor
    res = await client.post(
        "/api/kcd/validate",
        json={"codes": ["A001"]},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["results"][0]["is_valid"] is True
    assert data["results"][0]["is_notifiable"] is True


async def test_create_claim_성별제한없는_법정감염병_경고로그_찍힘(
    db, approved_doctor, kcd_codes, caplog
):
    """
    회귀 테스트: sex_restriction=None 인 법정감염병 코드(A001 콜레라)로
    create_claim() 호출 시 is_notifiable 경고 로그가 찍혀야 한다.

    수정 전 버그: is_notifiable 체크가 sex_restriction 블록 안에 중첩돼 있어서
    sex_restriction=None 이면 경고가 아예 실행되지 않았음.
    수정 후: 두 블록이 독립적으로 실행됨.
    """
    from app.billing.service import create_claim
    from app.core.models import Hospital, MedicalRecord, Patient

    doctor, _ = approved_doctor
    hospital = await db.get(Hospital, doctor.hospital_id)

    patient = Patient(
        hospital_id=hospital.id,
        name="테스트환자",
        gender="남",        # sex_restriction=None 이므로 성별 체크와 무관
        insurance_type="health",
    )
    db.add(patient)
    await db.flush()

    record = MedicalRecord(
        patient_id=patient.id,
        doctor_id=doctor.id,
        hospital_id=hospital.id,
        kcd_code="A001",    # sex_restriction=None, is_notifiable=True (콜레라)
        chart_structured="콜레라",
        status="completed",
    )
    db.add(record)
    await db.commit()

    with caplog.at_level(logging.WARNING, logger="app.billing.service"):
        try:
            await create_claim(
                db=db,
                hospital_id=hospital.id,
                doctor_id=doctor.id,
                patient_id=patient.id,
                medical_record_ids=[record.id],
                claim_period_year=2026,
                claim_period_month=6,
            )
        except Exception:
            pass  # 금액 계산 등 후속 로직 실패는 무관

    warning_messages = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    assert any("A001" in msg for msg in warning_messages), (
        "sex_restriction=None인 법정감염병 코드(A001)에서 "
        "is_notifiable 경고 로그가 찍히지 않았습니다. "
        "service.py의 is_notifiable 블록이 sex_restriction 블록 밖에 있는지 확인하세요.\n"
        f"실제 캡처된 WARNING 로그: {warning_messages}"
    )
