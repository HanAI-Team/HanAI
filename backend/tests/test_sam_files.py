"""generate_sam_files() — SAM File 생성 디렉토리용 개별 파일 분리 테스트.

한방 명세서는 H010(청구서, 공통) + K020.1(일반내역)~K020.4(특정내역)
4개 파일로 나뉜다. 파일 없음(레코드 없음)도 0바이트 더미 파일로 포함돼야 한다.
"""

from app.billing.edi_writer import (
    ClaimHeader,
    DiagnosisRecord,
    EDIFile,
    PatientRecord,
    RecordKey,
    build_claim_header,
    build_diagnosis_record,
    build_medlog_record,
    build_patient_record,
    generate_sam_files,
)

_KEY = RecordKey(claim_no="2026060001", record_serial=1)


def test_일곱개_파일이_모두_생성됨():
    edi = EDIFile(
        header=ClaimHeader(claim_no="2026060001", form_no="H010", institution_code="12345678", treatment_ym="202606", claim_date="20260601"),
        patient_records=[PatientRecord(key=_KEY, institution_code="12345678")],
    )
    files = generate_sam_files(edi)
    assert set(files.keys()) == {"H010", "K020.1", "K020.2", "K020.3", "K020.4", "H060", "MEDLOG.ENC"}


def test_H060은_항상_0바이트_더미():
    """치료재료 및 약제 구입내역통보서 — 이 앱은 구매내역 입력 기능이 없어 항상 0바이트."""
    edi = EDIFile(
        header=ClaimHeader(claim_no="2026060001", form_no="H010", institution_code="12345678", treatment_ym="202606", claim_date="20260601"),
        patient_records=[PatientRecord(key=_KEY, institution_code="12345678")],
    )
    files = generate_sam_files(edi)
    assert files["H060"] == b""


def test_레코드_없는_파일은_0바이트_더미():
    edi = EDIFile(
        header=ClaimHeader(claim_no="2026060001", form_no="H010", institution_code="12345678", treatment_ym="202606", claim_date="20260601"),
        patient_records=[PatientRecord(key=_KEY, institution_code="12345678")],
        # diagnosis_records, procedure_records, special_records 모두 미지정(빈 리스트)
    )
    files = generate_sam_files(edi)
    assert files["K020.2"] == b""
    assert files["K020.3"] == b""
    assert files["K020.4"] == b""


def test_H010은_헤더_레코드만_포함():
    header = ClaimHeader(claim_no="2026060001", form_no="H010", institution_code="12345678", treatment_ym="202606", claim_date="20260601")
    edi = EDIFile(header=header, patient_records=[PatientRecord(key=_KEY, institution_code="12345678")])
    files = generate_sam_files(edi)
    assert files["H010"] == build_claim_header(header).encode("euc-kr", errors="replace")


def test_K020_1은_환자_레코드만_포함():
    patient = PatientRecord(key=_KEY, institution_code="12345678", subscriber_name="홍길동")
    edi = EDIFile(
        header=ClaimHeader(claim_no="2026060001", form_no="H010", institution_code="12345678", treatment_ym="202606", claim_date="20260601"),
        patient_records=[patient],
    )
    files = generate_sam_files(edi)
    assert files["K020.1"] == build_patient_record(patient).encode("euc-kr", errors="replace")


def test_K020_2는_상병내역만_포함되고_다른_명세서_serial은_섞이지_않음():
    diag = DiagnosisRecord(
        key=_KEY, kcd_code="M5459", onset_date="20260601", treatment_dept=9,
        license_kind="3", license_no="12345",
    )
    other_diag = DiagnosisRecord(
        key=RecordKey(claim_no="2026060001", record_serial=2),
        kcd_code="M5460", onset_date="20260601", treatment_dept=9,
        license_kind="3", license_no="12345",
    )
    edi = EDIFile(
        header=ClaimHeader(claim_no="2026060001", form_no="H010", institution_code="12345678", treatment_ym="202606", claim_date="20260601"),
        patient_records=[PatientRecord(key=_KEY, institution_code="12345678")],
        diagnosis_records=[(1, diag), (2, other_diag)],
    )
    files = generate_sam_files(edi)
    # 두 진단 레코드 모두 K020.2에 순서대로 들어감 (patient 단위로 필터링하는
    # generate_edi()와 달리, SAM File은 레코드 종류 단위로 파일을 나누므로
    # 같은 파일 안에 여러 명세서의 상병내역이 순서대로 이어진다).
    expected = (build_diagnosis_record(diag) + build_diagnosis_record(other_diag)).encode(
        "euc-kr", errors="replace"
    )
    assert files["K020.2"] == expected


# ── 정보파일(MEDLOG.ENC) — 「전자문서작성요령」 별첨1 "라." 기준 ──────────────
# 2026-07-16 실측: 실제 상시점검 테스트로 만든 정상 MEDLOG.ENC 파일과
# 바이트 단위로 동일함을 확인.

def test_MEDLOG_거래처ID_부처ID_연결구분은_고정값():
    content = build_medlog_record("한방 청구SW 상시점검")
    lines = content.decode("euc-kr").split("\r\n")
    assert lines[0] == " " * 12          # 거래처ID(12) — 미사용, 공백
    assert lines[1] == "NULL" + " " * 4  # 부처ID(8) — 항상 'NULL'
    assert lines[3] == " " * 12          # 연결구분(12) — 미사용, 공백


def test_MEDLOG_문서제목이_30바이트로_패딩됨():
    content = build_medlog_record("한방 청구SW 상시점검")
    lines = content.decode("euc-kr").split("\r\n")
    title_line_bytes = lines[2].encode("euc-kr")
    assert len(title_line_bytes) == 30
    assert lines[2].rstrip() == "한방 청구SW 상시점검"


def test_MEDLOG_각_LINE은_CRLF로_구분되고_마지막_LINE_뒤에도_CRLF():
    content = build_medlog_record("한방 청구SW 상시점검")
    assert content.endswith(b"\r\n")
    assert content.count(b"\r\n") == 4  # 4개 항목 각각 + 마지막 LINE 뒤


def test_MEDLOG_실측파일과_바이트단위로_동일():
    """2026-07-16 상시점검 테스트로 실제 생성/검증된 MEDLOG.ENC 원본과 비교."""
    expected = (
        b"            \r\n"
        b"NULL    \r\n"
        b"\xc7\xd1\xb9\xe6 \xc3\xbb\xb1\xb8SW \xbb\xf3\xbd\xc3\xc1\xa1\xb0\xcb          \r\n"
        b"            \r\n"
    )
    assert build_medlog_record("한방 청구SW 상시점검") == expected


def test_MEDLOG는_SAM_File_생성시_자동으로_포함됨():
    edi = EDIFile(
        header=ClaimHeader(
            claim_no="2026070011", form_no="H010", institution_code="12345678",
            treatment_ym="202607", claim_date="20260701", writer="상시점검",
        ),
        patient_records=[PatientRecord(key=_KEY, institution_code="12345678")],
    )
    files = generate_sam_files(edi)
    assert files["MEDLOG.ENC"] == build_medlog_record("한방 청구SW 상시점검")


def test_MEDLOG_상시점검_아니면_청구번호_기반_제목():
    edi = EDIFile(
        header=ClaimHeader(
            claim_no="2026070011", form_no="H010", institution_code="12345678",
            treatment_ym="202607", claim_date="20260701", writer="홍길동",
        ),
        patient_records=[PatientRecord(key=_KEY, institution_code="12345678")],
    )
    files = generate_sam_files(edi)
    assert files["MEDLOG.ENC"] == build_medlog_record("2026070011 한방외래 청구")
