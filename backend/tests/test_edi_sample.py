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

2026-07-09 전면 재계산 2차: edi_writer.py가 별첨1(전자문서 교환방식/EDI) 기준으로
다시 전면 재작성되면서(레코드 키가 기관기호+일련번호+확장번호 17바이트에서
청구번호+명세서일련번호 15바이트로 변경, 상병내역이 별도 레코드로 분리,
EOF 레코드 제거 등) 이 파일의 모든 오프셋/길이 기댓값을 다시 계산했다.
레코드 길이가 전부 서로 달라 길이만으로 유일하게 구분 가능하다.
"""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select

from app.billing.service import generate_claim_edi
from app.core.models import (
    Claim,
    ClaimLineItem,
    DoctorWorkDays,
    Hospital,
    KcdUCode,
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
        rrn="900101-1234567",
    )
    db.add(patient)
    db.add(KcdUCode(
        code="M5459", korean_name="요통, 상세불명의 부위",
        effective_date=date(2000, 1, 1), expired_date=None,
    ))
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
# 2026-07-09 별첨1(EDI) 기준 오프셋 전면 재계산.
# (레코드4 특정내역기재란 레이아웃: KEY15 + 내역구분1 + 발생단위구분1 +
#  처방전발급번호13 + 줄번호4 + 특정내역구분5 + 특정내역700 = 739바이트)

def parse_lines(edi_bytes: bytes) -> list[bytes]:
    """CRLF 분리 후 빈 줄 제거."""
    return [l for l in edi_bytes.split(b"\r\n") if l]


def special_code(line: bytes) -> str:
    """레코드4 특정내역구분코드 (bytes 35-39, 1-indexed → [34:39] 0-indexed)."""
    return line[34:39].decode("euc-kr").strip()


def special_content(line: bytes) -> str:
    """레코드4 특정내역 내용 (bytes 40-739, 1-indexed → [39:739] 0-indexed)."""
    return line[39:739].decode("euc-kr").strip()


def record_line_no(line: bytes) -> int:
    """레코드4 줄번호 (bytes 31-34, 1-indexed → [30:34] 0-indexed)."""
    return int(line[30:34].decode("euc-kr"))


# ── 테스트: 레코드 수·길이 ────────────────────────────────────────────────────

async def test_EDI_레코드_수와_길이(db, 한의원_외래_사례):
    """
    기대 레코드 순서 및 바이트 길이 (2026-07-09 별첨1/EDI 재작성 반영):
      1  레코드1    심사청구서(헤더)    2096 bytes
      2  레코드2    명세서일반내역       325 bytes
      3  레코드2-1  명세서상병내역        43 bytes
      4  레코드3    초진진찰료            75 bytes
      5  레코드3    투자법침술            75 bytes
      6  레코드4    MT032 접수일시       739 bytes
      7  레코드4    JS010 줄1           739 bytes
      8  레코드4    JS010 줄2           739 bytes
      9  레코드4    JS011 경혈명        739 bytes

    (별첨1 기준에는 EOF 레코드가 없다.)
    """
    claim, hospital = 한의원_외래_사례
    edi = await generate_claim_edi(db, hospital.id, claim.id)
    records = parse_lines(edi)

    assert len(records) == 9, f"레코드 수 불일치: {len(records)}"

    # 레코드3(진료내역) 마지막 필드는 가감 등 구분 an(10), pos 66 → 75바이트
    expected = [2096, 325, 43, 75, 75, 739, 739, 739, 739]
    for i, (rec, exp) in enumerate(zip(records, expected)):
        assert len(rec) == exp, (
            f"레코드[{i}] 길이 불일치: 기대={exp}, 실제={len(rec)}"
        )


# ── 테스트: JS011 경혈명 ──────────────────────────────────────────────────────

async def test_JS011_경혈명_BL060_KI003(db, 한의원_외래_사례):
    claim, hospital = 한의원_외래_사례
    edi = await generate_claim_edi(db, hospital.id, claim.id)

    c2_08 = [r for r in parse_lines(edi) if len(r) == 739]
    js011 = next((r for r in c2_08 if special_code(r) == "JS011"), None)

    assert js011 is not None, "JS011 특정내역 레코드 없음"
    assert special_content(js011) == "BL060/KI003"


async def test_JS011_줄번호는_침술_라인(db, 한의원_외래_사례):
    """투자법침술은 두 번째 진료내역(줄2) → line_no=2."""
    claim, hospital = 한의원_외래_사례
    edi = await generate_claim_edi(db, hospital.id, claim.id)

    c2_08 = [r for r in parse_lines(edi) if len(r) == 739]
    js011 = next((r for r in c2_08 if special_code(r) == "JS011"), None)

    assert js011 is not None
    assert record_line_no(js011) == 2


# ── 테스트: MT032 접수일시 ────────────────────────────────────────────────────

async def test_MT032_접수일시_포함(db, 한의원_외래_사례):
    claim, hospital = 한의원_외래_사례
    edi = await generate_claim_edi(db, hospital.id, claim.id)

    c2_08 = [r for r in parse_lines(edi) if len(r) == 739]
    mt032 = next((r for r in c2_08 if special_code(r) == "MT032"), None)

    assert mt032 is not None, "MT032 특정내역 레코드 없음"
    assert special_content(mt032) == "202606012215"


# ── 테스트: JS010 진료일시 ────────────────────────────────────────────────────

async def test_JS010_진료내역_줄별_생성(db, 한의원_외래_사례):
    """진료내역 2줄 → JS010 2개, 각각 줄번호 1·2."""
    claim, hospital = 한의원_외래_사례
    edi = await generate_claim_edi(db, hospital.id, claim.id)

    c2_08 = [r for r in parse_lines(edi) if len(r) == 739]
    js010_list = [r for r in c2_08 if special_code(r) == "JS010"]

    assert len(js010_list) == 2, f"JS010 레코드 수 불일치: {len(js010_list)}"

    ext_nos = sorted(record_line_no(r) for r in js010_list)
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

    c2_08 = [r for r in parse_lines(edi) if len(r) == 739]
    mt050 = next((r for r in c2_08 if special_code(r) == "MT050"), None)

    assert mt050 is not None, "MT050 특정내역 레코드 없음"
    assert special_content(mt050) == "20260606/01.0/20260613/00.5"


async def test_MT050_근무현황_없으면_레코드_미생성(db, 한의원_외래_사례):
    """등록된 근무현황이 없으면 MT050 레코드를 생성하지 않는다."""
    claim, hospital = 한의원_외래_사례
    edi = await generate_claim_edi(db, hospital.id, claim.id)

    c2_08 = [r for r in parse_lines(edi) if len(r) == 739]
    mt050 = next((r for r in c2_08 if special_code(r) == "MT050"), None)

    assert mt050 is None


# ── 테스트: MT008 의사별 진료일수 ─────────────────────────────────────────────
# ※ HIRA 사례집(v089, 외래 사례1 "싱가포르")에서 실제 확인된 형식:
#   "의사생년월일(YYMMDD)/실제진료일수"를 의사별로 슬래시(/) 연결.
#   예: "YYMMDD/22/YYMMDD/20/YYMMDD/12"
#   시간제·격일제 1/2 계산·4사5입, 월 15일 상한, "기타" 인력 제외 등은
#   DoctorWorkDays 입력 시점에 이미 반영된 최종값이라고 가정 (입력 API 미구현 상태).
#   정렬 기준은 명시 스펙이 없어 id(입력 순서) 기준 — 재검증 필요.

async def test_MT008_의사별_진료일수_생년월일_슬래시연결(db, 한의원_외래_사례):
    claim, hospital = 한의원_외래_사례
    db.add_all([
        DoctorWorkDays(
            hospital_id=hospital.id, claim_period_year=2026, claim_period_month=6,
            doctor_birth_date="700101", work_days=22,
        ),
        DoctorWorkDays(
            hospital_id=hospital.id, claim_period_year=2026, claim_period_month=6,
            doctor_birth_date="750615", work_days=20,
        ),
        DoctorWorkDays(
            hospital_id=hospital.id, claim_period_year=2026, claim_period_month=6,
            doctor_birth_date="800320", work_days=12,
        ),
    ])
    await db.commit()

    edi = await generate_claim_edi(db, hospital.id, claim.id)

    c2_08 = [r for r in parse_lines(edi) if len(r) == 739]
    mt008 = next((r for r in c2_08 if special_code(r) == "MT008"), None)

    assert mt008 is not None, "MT008 특정내역 레코드 없음"
    assert special_content(mt008) == "700101/22/750615/20/800320/12"


async def test_MT008_다른_청구월_데이터는_제외(db, 한의원_외래_사례):
    """claim_period_year/month가 다른 DoctorWorkDays는 포함하지 않는다."""
    claim, hospital = 한의원_외래_사례
    db.add_all([
        DoctorWorkDays(
            hospital_id=hospital.id, claim_period_year=2026, claim_period_month=5,  # 5월 — 이번 청구(6월) 아님
            doctor_birth_date="700101", work_days=22,
        ),
    ])
    await db.commit()

    edi = await generate_claim_edi(db, hospital.id, claim.id)

    c2_08 = [r for r in parse_lines(edi) if len(r) == 739]
    mt008 = next((r for r in c2_08 if special_code(r) == "MT008"), None)

    assert mt008 is None


async def test_MT008_근무일수_없으면_레코드_미생성(db, 한의원_외래_사례):
    """등록된 DoctorWorkDays가 없으면 MT008 레코드를 생성하지 않는다."""
    claim, hospital = 한의원_외래_사례
    edi = await generate_claim_edi(db, hospital.id, claim.id)

    c2_08 = [r for r in parse_lines(edi) if len(r) == 739]
    mt008 = next((r for r in c2_08 if special_code(r) == "MT008"), None)

    assert mt008 is None


# ── 테스트: MT019 진료확인번호 ────────────────────────────────────────────────
# ※ HIRA 사례집(v089, 입원 사례 9-1~9-5, 전부 의료급여 환자)에서 실제 확인.
#   건강보험 환자 사례에는 전혀 등장하지 않아 "의료급여 환자만" 기재 조건으로 판단.
#   confirmation_no를 채우는 API가 아직 없어 Patient 컬럼값을 그대로 사용 —
#   실제 채번 규칙(13자리 형식) 검증은 API 구현 후 재검증 필요.

async def test_MT019_의료급여_환자_진료확인번호_포함(db, 한의원_외래_사례):
    claim, hospital = 한의원_외래_사례
    patient = await db.get(Patient, claim.patient_id)
    patient.insurance_type = "medical_aid"
    patient.confirmation_no = "2606010123456"
    await db.commit()

    edi = await generate_claim_edi(db, hospital.id, claim.id)

    c2_08 = [r for r in parse_lines(edi) if len(r) == 739]
    mt019 = next((r for r in c2_08 if special_code(r) == "MT019"), None)

    assert mt019 is not None, "MT019 특정내역 레코드 없음"
    assert special_content(mt019) == "2606010123456"


async def test_MT019_건강보험_환자는_미생성(db, 한의원_외래_사례):
    """insurance_type이 health(건강보험)면 confirmation_no가 있어도 MT019를 기재하지 않는다."""
    claim, hospital = 한의원_외래_사례
    patient = await db.get(Patient, claim.patient_id)
    patient.confirmation_no = "2606010123456"  # health 상태에서 실수로 채워진 경우 가정
    await db.commit()

    edi = await generate_claim_edi(db, hospital.id, claim.id)

    c2_08 = [r for r in parse_lines(edi) if len(r) == 739]
    mt019 = next((r for r in c2_08 if special_code(r) == "MT019"), None)

    assert mt019 is None


async def test_MT019_confirmation_no_없으면_미생성(db, 한의원_외래_사례):
    """의료급여 환자라도 confirmation_no가 비어있으면 MT019를 기재하지 않는다."""
    claim, hospital = 한의원_외래_사례
    patient = await db.get(Patient, claim.patient_id)
    patient.insurance_type = "medical_aid"
    await db.commit()

    edi = await generate_claim_edi(db, hospital.id, claim.id)

    c2_08 = [r for r in parse_lines(edi) if len(r) == 739]
    mt019 = next((r for r in c2_08 if special_code(r) == "MT019"), None)

    assert mt019 is None


# ── 테스트: 보완·추가청구 접수번호/명일련/사유코드 (레코드2) ──────────────────
# 2026-07-09: 모든 레코드 길이가 서로 달라서, 길이만으로 레코드2를 바로
# 고유하게 골라낼 수 있음.
# 접수번호(43-49,1-idx→[42:49]) / 명일련(50-54→[49:54]) / 사유(55-56→[54:56])

async def test_보완청구_접수번호_명일련_사유코드_반영(db, 한의원_외래_사례):
    claim, hospital = 한의원_외래_사례
    claim.claim_type = "supplement"
    claim.original_receipt_no = 1234567
    claim.original_record_serial = 5
    claim.rejection_reason_code = "12"
    await db.commit()

    edi = await generate_claim_edi(db, hospital.id, claim.id)
    c2_11_list = [r for r in parse_lines(edi) if len(r) == 325]
    assert len(c2_11_list) == 1, f"레코드2 수 불일치: {len(c2_11_list)}"
    c2_11 = c2_11_list[0]

    assert c2_11[42:49].decode("euc-kr") == "1234567"  # 43-49 접수번호
    assert c2_11[49:54].decode("euc-kr") == "00005"    # 50-54 명일련
    assert c2_11[54:56].decode("euc-kr") == "12"       # 55-56 사유


async def test_최초청구는_접수번호_공란(db, 한의원_외래_사례):
    """claim_type 미지정(최초청구) 시 접수번호/명일련은 0, 사유는 공란."""
    claim, hospital = 한의원_외래_사례
    edi = await generate_claim_edi(db, hospital.id, claim.id)
    c2_11_list = [r for r in parse_lines(edi) if len(r) == 325]
    assert len(c2_11_list) == 1, f"레코드2 수 불일치: {len(c2_11_list)}"
    c2_11 = c2_11_list[0]

    assert c2_11[42:49].decode("euc-kr") == "0000000"
    assert c2_11[49:54].decode("euc-kr") == "00000"
    assert c2_11[54:56].decode("euc-kr") == "  "


# ── 테스트: 상병분류기호/주민등록번호 방어 검증 (MCPoS 04-04/10-02 회귀) ──────

async def test_상병분류기호_미등록코드면_SAM생성_차단(db, 한의원_외래_사례):
    """kcd_code가 완전코드 목록(KcdUCode)에 없으면(예: "초진" 같은 오염값) SAM 생성을 막는다."""
    claim, hospital = 한의원_외래_사례
    r = await db.execute(select(MedicalRecord).where(MedicalRecord.claim_id == claim.id))
    record = r.scalars().first()
    record.kcd_code = "초진"
    await db.commit()

    with pytest.raises(HTTPException) as exc_info:
        await generate_claim_edi(db, hospital.id, claim.id)
    assert exc_info.value.status_code == 400


async def test_수진자_주민등록번호_누락시_SAM생성_차단(db, 한의원_외래_사례):
    """환자 주민등록번호가 없으면 더미값(0)으로 채우지 않고 SAM 생성을 막는다."""
    claim, hospital = 한의원_외래_사례
    r = await db.execute(select(Patient).where(Patient.id == claim.patient_id))
    patient = r.scalar_one()
    patient.rrn = None
    await db.commit()

    with pytest.raises(HTTPException) as exc_info:
        await generate_claim_edi(db, hospital.id, claim.id)
    assert exc_info.value.status_code == 400


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
