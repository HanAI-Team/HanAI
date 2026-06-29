"""
심평원 청구SW 기능검사 사례데이터 기반 EDI 생성 테스트.

사례: 한의원 / 한의과 외래 / 건강보험(4)
  - 상병: M5459 (요통, 상세불명의 부위)
  - 진료내역:
      줄1  항01 목01  10100011  초진진찰료(야간-차등수가제외)  11,560원
      줄2  항04 목01  40080010  투자법 침술(야간)              4,220원
  - 특정내역:
      MT032  접수일시
      JS010  진료일시 (줄별)
      JS011  경혈명  BL060/KI003  (줄2)

기대 출력값(HIRA)을 받은 뒤 test_HIRA_기대출력_정확일치 에 경로를 지정하면
바이트 단위 정합성까지 검증한다.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
import pytest_asyncio

from app.billing.service import generate_claim_edi
from app.core.models import (
    Claim,
    ClaimLineItem,
    Hospital,
    MedicalRecord,
    Patient,
    SaturdayHolidayStaffing,
)

# 사례 데이터 고정값
VISIT_DT = datetime(2026, 6, 1, 22, 15, tzinfo=timezone.utc)  # 야간 진료
EXPECTED_EDI_PATH = Path(__file__).parent / "fixtures" / "한의원_외래_사례_expected.edi"


# ── 픽스처 ────────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def 한의원_외래_사례(db, approved_doctor):
    """심평원 사례데이터를 DB에 세팅하고 (claim, hospital) 반환."""
    doctor, _ = approved_doctor

    hospital = await db.get(Hospital, doctor.hospital_id)
    hospital.institution_code = "12345678"
    await db.flush()

    patient = Patient(
        hospital_id=hospital.id,
        name="한의외1",
        insurance_type="health",
    )
    db.add(patient)
    await db.flush()

    record = MedicalRecord(
        patient_id=patient.id,
        doctor_id=doctor.id,
        hospital_id=hospital.id,
        kcd_code="M5459",
        chart_structured="요통, 상세불명의 부위",
        recorded_at=VISIT_DT,
        status="completed",
    )
    db.add(record)
    await db.flush()

    total = 11560 + 4220
    claim = Claim(
        id=uuid.uuid4(),
        patient_id=patient.id,
        doctor_id=doctor.id,
        hospital_id=hospital.id,
        claim_period_year=2026,
        claim_period_month=6,
        total_amount=total,
        patient_copay=round(total * 0.30),
        claim_amount=total - round(total * 0.30),
        status="draft",
    )
    db.add(claim)
    record.claim_id = claim.id
    await db.flush()

    # 사례 진료내역 그대로 ClaimLineItem 생성
    db.add_all([
        ClaimLineItem(
            claim_id=claim.id,
            medical_record_id=record.id,
            hang="01", mok="01",
            code="10100011",
            name="초진진찰료(야간-차등수가제외)",
            unit_price=11560, qty=1, days=1, amount=11560,
        ),
        ClaimLineItem(
            claim_id=claim.id,
            medical_record_id=record.id,
            hang="04", mok="01",
            code="40080010",
            name="투자법 침술(야간)",
            unit_price=4220, qty=1, days=1, amount=4220,
            hyeolmyeong_names=["BL060", "KI003"],
        ),
    ])
    await db.commit()
    return claim, hospital


# ── EDI 파싱 헬퍼 ─────────────────────────────────────────────────────────────

def parse_lines(edi_bytes: bytes) -> list[bytes]:
    """CRLF 분리 후 빈 줄 제거."""
    return [l for l in edi_bytes.split(b"\r\n") if l]


def special_code(line: bytes) -> str:
    """C2-08 특정내역구분코드 (bytes 43-47, 1-indexed → [42:47] 0-indexed)."""
    return line[42:47].decode("euc-kr").strip()


def special_content(line: bytes) -> str:
    """C2-08 특정내역 내용 (bytes 48-747, 1-indexed → [47:747] 0-indexed)."""
    return line[47:747].decode("euc-kr").strip()


def record_ext_no(line: bytes) -> int:
    """C2-08 진료내역확장번호 = 줄번호 (bytes 39-42 → [38:42])."""
    return int(line[38:42].decode("euc-kr"))


# ── 테스트: 레코드 수·길이 ────────────────────────────────────────────────────

async def test_EDI_레코드_수와_길이(db, 한의원_외래_사례):
    """
    기대 레코드 순서 및 바이트 길이:
      1  C2-00  심사청구서         345 bytes
      2  C2-11  명세서일반내역      345 bytes
      3  C2-02  명세서상병내역       89 bytes
      4  C2-13  초진진찰료         291 bytes
      5  C2-13  투자법침술         291 bytes
      6  C2-08  MT032 접수일시     747 bytes
      7  C2-08  JS010 줄1         747 bytes
      8  C2-08  JS010 줄2         747 bytes
      9  C2-08  JS011 경혈명      747 bytes
     10  C2-09  EOF               20 bytes
    """
    claim, hospital = 한의원_외래_사례
    edi = await generate_claim_edi(db, hospital.id, claim.id)
    records = parse_lines(edi)

    assert len(records) == 10, f"레코드 수 불일치: {len(records)}"

    expected = [345, 345, 89, 291, 291, 747, 747, 747, 747, 20]
    for i, (rec, exp) in enumerate(zip(records, expected)):
        assert len(rec) == exp, (
            f"레코드[{i}] 길이 불일치: 기대={exp}, 실제={len(rec)}"
        )


# ── 테스트: JS011 경혈명 ──────────────────────────────────────────────────────

async def test_JS011_경혈명_BL060_KI003(db, 한의원_외래_사례):
    claim, hospital = 한의원_외래_사례
    edi = await generate_claim_edi(db, hospital.id, claim.id)

    c2_08 = [r for r in parse_lines(edi) if len(r) == 747]
    js011 = next((r for r in c2_08 if special_code(r) == "JS011"), None)

    assert js011 is not None, "JS011 특정내역 레코드 없음"
    assert special_content(js011) == "BL060/KI003"


async def test_JS011_줄번호는_침술_라인(db, 한의원_외래_사례):
    """투자법침술은 두 번째 진료내역(줄2) → record_ext_no=2."""
    claim, hospital = 한의원_외래_사례
    edi = await generate_claim_edi(db, hospital.id, claim.id)

    c2_08 = [r for r in parse_lines(edi) if len(r) == 747]
    js011 = next((r for r in c2_08 if special_code(r) == "JS011"), None)

    assert js011 is not None
    assert record_ext_no(js011) == 2


# ── 테스트: MT032 접수일시 ────────────────────────────────────────────────────

async def test_MT032_접수일시_포함(db, 한의원_외래_사례):
    claim, hospital = 한의원_외래_사례
    edi = await generate_claim_edi(db, hospital.id, claim.id)

    c2_08 = [r for r in parse_lines(edi) if len(r) == 747]
    mt032 = next((r for r in c2_08 if special_code(r) == "MT032"), None)

    assert mt032 is not None, "MT032 특정내역 레코드 없음"
    assert special_content(mt032) == "202606012215"


# ── 테스트: JS010 진료일시 ────────────────────────────────────────────────────

async def test_JS010_진료내역_줄별_생성(db, 한의원_외래_사례):
    """진료내역 2줄 → JS010 2개, 각각 줄번호 1·2."""
    claim, hospital = 한의원_외래_사례
    edi = await generate_claim_edi(db, hospital.id, claim.id)

    c2_08 = [r for r in parse_lines(edi) if len(r) == 747]
    js010_list = [r for r in c2_08 if special_code(r) == "JS010"]

    assert len(js010_list) == 2, f"JS010 레코드 수 불일치: {len(js010_list)}"

    ext_nos = sorted(record_ext_no(r) for r in js010_list)
    assert ext_nos == [1, 2], f"JS010 줄번호 불일치: {ext_nos}"

    for r in js010_list:
        assert special_content(r) == "202606012215"


# ── 테스트: MT050 토요일·공휴일 근무현황 ─────────────────────────────────────
# ※ content 바이트 레이아웃("YYYYMMDD/인원수"를 슬래시로 연결)은 공식 작성요령
#   문서를 확보하지 못한 상태의 추정값. 공식 스펙 확보 시 재검증 필요.

async def test_MT050_근무현황_날짜인원수_슬래시연결(db, 한의원_외래_사례):
    claim, hospital = 한의원_외래_사례
    db.add_all([
        SaturdayHolidayStaffing(hospital_id=hospital.id, work_date=date(2026, 6, 6), doctor_count=Decimal("1.0")),
        SaturdayHolidayStaffing(hospital_id=hospital.id, work_date=date(2026, 6, 13), doctor_count=Decimal("0.5")),
    ])
    await db.commit()

    edi = await generate_claim_edi(db, hospital.id, claim.id)

    c2_08 = [r for r in parse_lines(edi) if len(r) == 747]
    mt050 = next((r for r in c2_08 if special_code(r) == "MT050"), None)

    assert mt050 is not None, "MT050 특정내역 레코드 없음"
    assert special_content(mt050) == "20260606/01.0/20260613/00.5"


async def test_MT050_근무현황_없으면_레코드_미생성(db, 한의원_외래_사례):
    """등록된 근무현황이 없으면 MT050 레코드를 생성하지 않는다."""
    claim, hospital = 한의원_외래_사례
    edi = await generate_claim_edi(db, hospital.id, claim.id)

    c2_08 = [r for r in parse_lines(edi) if len(r) == 747]
    mt050 = next((r for r in c2_08 if special_code(r) == "MT050"), None)

    assert mt050 is None


# ── 테스트: HIRA 기대 출력값 정확 일치 (파일 있을 때만 실행) ──────────────────

@pytest.mark.skipif(
    not EXPECTED_EDI_PATH.exists(),
    reason="HIRA 기대 출력 파일 없음 — 검사사례관리에서 다운로드 후 "
           f"tests/fixtures/한의원_외래_사례_expected.edi 에 저장",
)
async def test_HIRA_기대출력_정확일치(db, 한의원_외래_사례):
    """HIRA가 제공한 기대 출력값과 바이트 단위 정확 일치 검증."""
    claim, hospital = 한의원_외래_사례
    edi = await generate_claim_edi(db, hospital.id, claim.id)
    assert edi == EXPECTED_EDI_PATH.read_bytes()
