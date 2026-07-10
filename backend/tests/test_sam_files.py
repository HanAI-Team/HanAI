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
    build_patient_record,
    generate_sam_files,
)

_KEY = RecordKey(claim_no="2026060001", record_serial=1)


def test_다섯개_파일이_모두_생성됨():
    edi = EDIFile(
        header=ClaimHeader(claim_no="2026060001", form_no="H010", institution_code="12345678", treatment_ym="202606", claim_date="20260601"),
        patient_records=[PatientRecord(key=_KEY, institution_code="12345678")],
    )
    files = generate_sam_files(edi)
    assert set(files.keys()) == {"H010", "K020.1", "K020.2", "K020.3", "K020.4"}


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
