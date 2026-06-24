"""EDI 파일 생성기.

HIRA 전산매체파일 수록사양 U1 (의치과 및 한방) 기준.
LAY 파일 C2-00, C2-11, C2-02, C2-71, C2-08, C2-09 레이아웃 적용.

자료구분 코드:
  '0': 요양급여비용 심사청구서   (C2-00, 345 bytes)
  '1': 명세서일반내역            (C2-11, 347 bytes)
  '2': 명세서상병내역            (C2-02,  91 bytes)
  '3': 명세서진료내역(의치과및한방) (C2-13)
  '8': 명세서특정내역            (C2-08, 747 bytes)
  '9': 마지막 정보파일(EOF)      (C2-09,  20 bytes)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

# ---------------------------------------------------------------------------
# 기본 포맷팅 함수
# ---------------------------------------------------------------------------

def _fmt9(value: int | None, length: int) -> str:
    """숫자 필드: 우측 정렬, 좌측 0 채움."""
    v = 0 if value is None else int(value)
    return str(v).zfill(length)[-length:]  # 자릿수 초과 시 우측 기준으로 자름


def _fmt9v9(value: Decimal | None, int_digits: int, dec_digits: int) -> str:
    """소수점 포함 숫자 필드 (V = 소수점 위치, 파일에는 소수점 문자 없이 기록).

    예) 9V9(7): int_digits=4, dec_digits=3 → "1234567"
    """
    total = int_digits + dec_digits
    if value is None:
        return "0" * total
    scaled = int(value * (10 ** dec_digits))
    return str(scaled).zfill(total)[-total:]


def _fmtx(value: str | None, length: int) -> str:
    """문자 필드: 좌측 정렬, 우측 공백 채움."""
    s = (value or "").encode("euc-kr", errors="replace").decode("euc-kr")
    # EUC-KR 바이트 기준 길이 맞춤 (한글 1자 = 2바이트)
    encoded = s.encode("euc-kr", errors="replace")
    if len(encoded) >= length:
        # 바이트 단위로 자르되 멀티바이트 경계 안전하게 처리
        truncated = encoded[:length]
        try:
            truncated.decode("euc-kr")
        except UnicodeDecodeError:
            truncated = encoded[:length - 1] + b" "
        return truncated.decode("euc-kr")
    return s + " " * ((length - len(encoded)))


def _build(parts: list[str], total: int) -> str:
    """파트 목록을 합쳐 total 바이트 레코드 + CRLF 반환."""
    record = "".join(parts)
    encoded = record.encode("euc-kr", errors="replace")
    # 길이 검증 (CRLF 제외)
    if len(encoded) != total:
        raise ValueError(
            f"레코드 길이 불일치: 기대={total}, 실제={len(encoded)}\n"
            f"레코드 내용: {record!r}"
        )
    return record + "\r\n"


# ---------------------------------------------------------------------------
# 공통 KEY 필드 (모든 레코드 앞부분)
# ---------------------------------------------------------------------------

@dataclass
class RecordKey:
    institution_code: str   # 요양기관기호 9(8)
    serial_no: int          # 명세서일련번호 9(5)
    ext_no: int = 0         # 확장번호 9(4)


def _key_parts(key: RecordKey) -> list[str]:
    return [
        _fmt9(int(key.institution_code), 8),
        _fmt9(key.serial_no, 5),
        _fmt9(key.ext_no, 4),
    ]


# ---------------------------------------------------------------------------
# C2-00: 요양급여비용(의료급여비용)심사청구서 (345 bytes)
# ---------------------------------------------------------------------------

@dataclass
class ClaimHeader:
    key: RecordKey
    billing_type: str       # 수록사양번호 XX: U1=의치과·한방
    treatment_ym: str       # 진료년월 CCYYMM (예: "202506")
    claim_date: str         # 청구일자 CCYYMMDD
    claimer: str            # 청구인 X(12)
    writer: str             # 작성자 X(12)
    writer_rrn: str         # 작성자주민등록번호 9(13)
    claim_count: int        # 청구건수
    benefit_total_1: int    # 요양급여비용총액1
    copayment: int          # 본인일부부담금
    claim_amount: int       # 청구액
    upper_limit_excess: int = 0
    disability_medical_cost: int = 0
    graduated_claim: int = 0
    graduated_index: Decimal = Decimal("0")
    treatment_days: Decimal = Decimal("0")
    doctor_count: Decimal = Decimal("0")
    approval_no: str = ""   # 검사승인번호 X(35)
    benefit_total_2: int = 0
    veterans_claim: int = 0
    support_fund: int = 0
    full_price_copay_total: int = 0
    veterans_copay: int = 0
    under_full_total: int = 0
    under_full_copay: int = 0
    under_full_claim: int = 0
    under_full_veterans_claim: int = 0


def build_claim_header(h: ClaimHeader) -> str:
    """C2-00 심사청구서 레코드 생성 (345 bytes + CRLF).

    레이아웃 (LAY C2-00 U1):
      1-  17: KEY (요양기관기호8 + 일련번호5 + 확장번호4)
     18-  19: 서식번호 '00'
     20-  21: 수록사양번호 'U1'
     22-  23: 진료분야구분
     24-  41: 공란(18)
     42-  47: 진료년월 CCYYMM
     48-  55: 청구일자 CCYYMMDD
     56-  67: 청구인(12)
     68-  79: 작성자(12)
     80-  92: 작성자주민등록번호(13)
     93- 100: 공란(8)
    101- 106: 청구건수(6)
    107- 118: 요양급여비용총액1(12)
    119- 130: 본인일부부담금(12)
    131- 142: 청구액(12)
    143- 154: 본인부담상한액초과금총액(12)
    155- 166: 장애인의료비(의료급여)(12)
    167- 176: 차등수가청구액(10)
    177- 183: 차등지수 9V9(7)
    184- 191: 진료일수 9999V99(8)
    192- 195: 의사수 99V99(4)
    196- 200: 대행청구단체(5)
    201- 235: 검사승인번호(35)
    236- 247: 요양급여비용총액2/진료비총액(12)
    248- 259: 보훈청구액(12)
    260- 271: 지원금(12)
    272- 283: 건강보험(의료급여) 100분의100 본인부담금총액(12)
    284- 295: 보훈 본인일부부담금(12)
    296- 300: 공란(5)
    301- 312: 100분의100미만 총액(12)
    313- 324: 100분의100미만 본인일부부담금(12)
    325- 336: 100분의100미만 청구액(12)
    337- 345: 100분의100미만 보훈청구액(9)
    """
    parts = [
        *_key_parts(h.key),                                          # 1-17
        _fmt9(0, 2),                                                 # 18-19  서식번호
        _fmtx(h.billing_type, 2),                                    # 20-21  수록사양번호
        _fmt9(0, 2),                                                 # 22-23  진료분야구분
        _fmtx("", 18),                                               # 24-41  공란
        _fmt9(int(h.treatment_ym), 6),                               # 42-47  진료년월
        _fmt9(int(h.claim_date), 8),                                 # 48-55  청구일자
        _fmtx(h.claimer, 12),                                        # 56-67  청구인
        _fmtx(h.writer, 12),                                         # 68-79  작성자
        _fmt9(int(h.writer_rrn.replace("-", "")), 13),               # 80-92  작성자주민등록번호
        _fmtx("", 8),                                                # 93-100 공란
        _fmt9(h.claim_count, 6),                                     # 101-106 청구건수
        _fmt9(h.benefit_total_1, 12),                                # 107-118 요양급여비용총액1
        _fmt9(h.copayment, 12),                                      # 119-130 본인일부부담금
        _fmt9(h.claim_amount, 12),                                   # 131-142 청구액
        _fmt9(h.upper_limit_excess, 12),                             # 143-154 본인부담상한액초과금
        _fmt9(h.disability_medical_cost, 12),                        # 155-166 장애인의료비
        _fmt9(h.graduated_claim, 10),                                # 167-176 차등수가청구액
        _fmt9v9(h.graduated_index, 4, 3),                            # 177-183 차등지수
        _fmt9v9(h.treatment_days, 6, 2),                             # 184-191 진료일수
        _fmt9v9(h.doctor_count, 2, 2),                               # 192-195 의사수
        _fmtx("", 5),                                                # 196-200 대행청구단체
        _fmtx(h.approval_no, 35),                                    # 201-235 검사승인번호
        _fmt9(h.benefit_total_2, 12),                                # 236-247 요양급여비용총액2
        _fmt9(h.veterans_claim, 12),                                 # 248-259 보훈청구액
        _fmt9(h.support_fund, 12),                                   # 260-271 지원금
        _fmt9(h.full_price_copay_total, 12),                         # 272-283 건강보험(의료급여) 100분의100 본인부담금총액
        _fmt9(h.veterans_copay, 12),                                 # 284-295 보훈 본인일부부담금
        _fmtx("", 5),                                                # 296-300 공란
        _fmt9(h.under_full_total, 12),                               # 301-312 100분의100미만 총액
        _fmt9(h.under_full_copay, 12),                               # 313-324 100분의100미만 본인일부부담금
        _fmt9(h.under_full_claim, 12),                               # 325-336 100분의100미만 청구액
        _fmt9(h.under_full_veterans_claim, 9),                       # 337-345 100분의100미만 보훈청구액
    ]
    return _build(parts, 345)


# ---------------------------------------------------------------------------
# C2-11: 명세서일반내역 (의치과 및 한방, 347 bytes)
# ---------------------------------------------------------------------------

@dataclass
class PatientRecord:
    key: RecordKey
    employer_code: str      # 사업장기호(보장기관기호) X(11)
    cert_no: str            # 증번호(보장기관승인번호) X(13)
    subscriber_name: str    # 가입자성명(세대주성명) X(12)
    patient_name: str       # 수진자성명 X(12)
    patient_rrn: str        # 수진자주민등록번호 9(13)
    inpatient_days: int     # 입내원일수
    benefit_days: int       # 요양급여일수
    benefit_total_1: int    # 요양급여비용총액1
    copayment: int          # 본인일부부담금
    claim_amount: int       # 청구액
    upper_limit_excess: int = 0
    medical_aid_type: str = " "   # 의료급여종별구분 A (1종=1, 2종=2, 공란=공란)
    deferred_or_disability: int = 0  # 대불금 또는 장애인의료비
    receipt_no: int = 0     # 접수번호 9(7)
    record_serial: int = 0  # 명일련 9(5)
    reason_code: str = "  " # 사유 XX
    first_admission_date: str = "00000000"  # 최초입원개시일 9(8)
    benefit_total_2: int = 0
    veterans_claim: int = 0
    support_fund: int = 0
    full_price_copay_total: int = 0  # 건강보험(의료급여) 100분의100 본인부담금총액
    veterans_copay: int = 0          # 보훈 본인일부부담금
    under_full_total: int = 0        # 100분의100미만 총액
    under_full_copay: int = 0        # 100분의100미만 본인일부부담금
    under_full_claim: int = 0        # 100분의100미만 청구액
    under_full_veterans_claim: int = 0  # 100분의100미만 보훈청구액


def build_patient_record(p: PatientRecord) -> str:
    """C2-11 명세서일반내역 레코드 생성 (345 bytes data + CRLF = Max 347).

    LAY C2-11 U1 (의치과 및 한방) — Max 347 = data 345 + CRLF 2:

    ROW 1 (1-100):
      1-  17: KEY
     18-  19: 서식번호 '01' (99형)
     20-  30: 사업장기호(보장기관기호) X(11)
     31-  34: 증번호앞 X(4)
     35-  43: 증번호뒤/공란 X(9)
     44-  55: 가입자성명(세대주성명) X(12)
     56-  67: 수진자성명 X(12)
     68-  80: 수진자주민등록번호 9(13)
     81-  83: 입내원일수 9(3)
     84-  86: 요양급여일수 9(3)
     87    : 공란 X(1)
     88- 100: 공란 X(13)

    ROW 2 (101-200):
    101- 127: 공란 X(27)
    128- 137: 요양급여비용총액1 9(10)
    138- 147: 본인일부부담금 9(10)
    148- 157: 청구액 9(10)
    158- 167: 본인부담상한액초과금 9(10)
    168- 188: 공란 X(21)
    189- 200: 공란 X(12)

    ROW 3 (201-300):
    201    : 의료급여종별구분 A X(1)  ※ 1종=1, 2종=2, 해당없음=공란
    202    : 공란 B X(1)
    203- 212: 대불금/장애인의료비 9(10)
    213- 219: 접수번호 9(7)
    220- 224: 명일련 9(5)
    225- 226: 사유 X(2)
    227    : 공란 X(1)
    228- 235: 최초입원개시일 9(8)
    236- 245: 요양급여비용총액2/진료비총액 9(10)
    246- 255: 보훈청구액 9(10)
    256- 265: 지원금 9(10)
    266- 275: 공란 9(10)
    276- 285: 공란 9(10)
    286- 295: 건강보험(의료급여) 100분의100 본인부담금총액 9(10)
    296- 305: 보훈 본인일부부담금 9(10)  ← row 경계 걸침

    ROW 4 (301-345 data, 346-347 CRLF):
    [301-305: 보훈 본인일부부담금 tail — 위 field 연속]
    306- 315: 100분의100미만 총액 9(10)
    316- 325: 100분의100미만 본인일부부담금 9(10)
    326- 335: 100분의100미만 청구액 9(10)
    336- 345: 100분의100미만 보훈청구액 9(10)
    346- 347: CRLF (Max 347에 포함)
    """
    parts = [
        # ROW 1
        *_key_parts(p.key),                                      # 1-17
        _fmt9(1, 2),                                             # 18-19   서식번호
        _fmtx(p.employer_code, 11),                              # 20-30   사업장기호
        _fmtx(p.cert_no[:4], 4),                                 # 31-34   증번호 앞
        _fmtx(p.cert_no[4:] if len(p.cert_no) > 4 else "", 9),  # 35-43   증번호 뒤/공란
        _fmtx(p.subscriber_name, 12),                            # 44-55   가입자성명
        _fmtx(p.patient_name, 12),                               # 56-67   수진자성명
        _fmt9(int(p.patient_rrn.replace("-", "")), 13),          # 68-80   주민등록번호
        _fmt9(p.inpatient_days, 3),                              # 81-83   입내원일수
        _fmt9(p.benefit_days, 3),                                # 84-86   요양급여일수
        _fmtx("", 1),                                            # 87      공란
        _fmtx("", 13),                                           # 88-100  공란
        # ROW 2
        _fmtx("", 27),                                           # 101-127 공란
        _fmt9(p.benefit_total_1, 10),                            # 128-137 요양급여비용총액1
        _fmt9(p.copayment, 10),                                  # 138-147 본인일부부담금
        _fmt9(p.claim_amount, 10),                               # 148-157 청구액
        _fmt9(p.upper_limit_excess, 10),                         # 158-167 본인부담상한액초과금
        _fmtx("", 21),                                           # 168-188 공란
        _fmtx("", 12),                                           # 189-200 공란
        # ROW 3
        _fmtx(p.medical_aid_type, 1),                            # 201     의료급여종별구분 A
        _fmtx("", 1),                                            # 202     공란 B
        _fmt9(p.deferred_or_disability, 10),                     # 203-212 대불금/장애인의료비
        _fmt9(p.receipt_no, 7),                                  # 213-219 접수번호
        _fmt9(p.record_serial, 5),                               # 220-224 명일련
        _fmtx(p.reason_code, 2),                                 # 225-226 사유
        _fmtx("", 1),                                            # 227     공란
        _fmt9(int(p.first_admission_date), 8),                   # 228-235 최초입원개시일
        _fmt9(p.benefit_total_2, 10),                            # 236-245 요양급여비용총액2
        _fmt9(p.veterans_claim, 10),                             # 246-255 보훈청구액
        _fmt9(p.support_fund, 10),                               # 256-265 지원금
        _fmtx("", 10),                                           # 266-275 공란
        _fmtx("", 10),                                           # 276-285 공란
        _fmt9(p.full_price_copay_total, 10),                     # 286-295 건강보험(의료급여) 100분의100
        # ROW 3→4 경계 걸치는 field
        _fmt9(p.veterans_copay, 10),                             # 296-305 보훈 본인일부부담금
        # ROW 4
        _fmt9(p.under_full_total, 10),                           # 306-315 100분의100미만 총액
        _fmt9(p.under_full_copay, 10),                           # 316-325 100분의100미만 본인일부부담금
        _fmt9(p.under_full_claim, 10),                           # 326-335 100분의100미만 청구액
        _fmt9(p.under_full_veterans_claim, 10),                  # 336-345 100분의100미만 보훈청구액
    ]
    return _build(parts, 345)


# ---------------------------------------------------------------------------
# C2-02: 명세서상병내역 (91 bytes)
# ---------------------------------------------------------------------------

@dataclass
class DiagnosisRecord:
    key: RecordKey
    kcd_code: str           # 상병분류기호 X(6)
    onset_date: str         # 당월요양개시일 X(8)
    treatment_dept: int     # 진료과목 99
    inpatient_route: int    # 입원경로 99
    prior_dept: int         # 세부전문과목 99
    license_kind: str       # 면허종류 X(1)
    license_no: str         # 면허번호 X(10)


def build_diagnosis_record(d: DiagnosisRecord) -> str:
    """C2-02 명세서상병내역 레코드 생성 (data 89 bytes + CRLF = Max 91).

    LAY C2-02 — Max 91 = data 89 + CRLF 2:
      1-  17: KEY (서식번호 없음 — C2-02는 KEY 직후 공란X(3))
     18-  20: 공란 X(3)
     21-  26: 상병분류기호 X(6)
     27-  34: 당월요양개시일(내원일자/조제투약일자) X(8)
     35-  36: 진료과목 99(2)
     37-  38: 입원경로 99(2)
     39-  40: 세부전문과목 99(2)
     41-  43: 공란 X(3)
     44-  75: 치식사항 4×X(8)=32 (치과용, 한방은 공란)
     76    : 면허종류 A X(1)  ※ A : 면허종류
     77-  86: 면허번호 X(10)
     87-  89: 공란 X(3)
     90-  91: CRLF (Max 91에 포함)
    """
    parts = [
        *_key_parts(d.key),              # 1-17
        _fmtx("", 3),                    # 18-20  공란
        _fmtx(d.kcd_code, 6),           # 21-26  상병분류기호
        _fmtx(d.onset_date, 8),         # 27-34  당월요양개시일
        _fmt9(d.treatment_dept, 2),      # 35-36  진료과목
        _fmt9(d.inpatient_route, 2),     # 37-38  입원경로
        _fmt9(d.prior_dept, 2),          # 39-40  세부전문과목
        _fmtx("", 3),                    # 41-43  공란
        _fmtx("", 32),                   # 44-75  치식사항 (한방은 공란)
        _fmtx(d.license_kind, 1),        # 76     면허종류
        _fmtx(d.license_no, 10),         # 77-86  면허번호
        _fmtx("", 3),                    # 87-89  공란
    ]
    return _build(parts, 89)


# ---------------------------------------------------------------------------
# C2-08: 명세서특정내역 (747 bytes)
# ---------------------------------------------------------------------------

@dataclass
class SpecialRecord:
    key: RecordKey
    prescription_no: int    # 처방전교부번호 9(13)
    record_ext_no: int      # 진료내역확장번호 9(4)
    special_code: str       # 특정내역구분 X(5)
    content: str            # 특정내역 X(700)


def build_special_record(s: SpecialRecord) -> str:
    """C2-08 명세서특정내역 레코드 생성 (747 bytes + CRLF).

    레이아웃 (LAY C2-08):
      1-  17: KEY
     18-  19: 서식번호 '08'
     20-  24: 공란(5)
     25    : 공란(1)
     26-  38: 처방전교부번호(13)
     39-  42: 진료내역확장번호(4)
     43-  47: 특정내역구분(5)
     48- 747: 특정내역(700)
    """
    parts = [
        *_key_parts(s.key),                    # 1-17
        _fmt9(8, 2),                           # 18-19  서식번호
        _fmtx("", 5),                          # 20-24  공란
        _fmtx("", 1),                          # 25     공란
        _fmt9(s.prescription_no, 13),          # 26-38  처방전교부번호
        _fmt9(s.record_ext_no, 4),             # 39-42  진료내역확장번호
        _fmtx(s.special_code, 5),              # 43-47  특정내역구분
        _fmtx(s.content, 700),                 # 48-747 특정내역
    ]
    return _build(parts, 747)


# ---------------------------------------------------------------------------
# C2-09: 마지막 정보파일 EOF (20 bytes)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# C2-13: 명세서진료내역(의치과및한방) (291 bytes)
# ---------------------------------------------------------------------------

@dataclass
class ProcedureDetail:
    key: RecordKey
    hang: str           # 항번호 XX (예: "04" = 시술및처치료)
    mok: str            # 목번호 99 (예: "01" = 침술)
    code_gubun: str     # 코드구분 X(1) (A=수가 B=전용 C=약가 H=치료재료)
    code: str           # 행위코드 X(8)
    unit_price: Decimal # 단가 9(9)V9
    qty: Decimal        # 1일투여량/실시횟수 9(4)V9999
    days: int           # 총투여일수/실시횟수 9(3)
    amount: int         # 금액 9(10)
    license_type: str   # 면허종류 X(1) (3=한의사 6=간호사 7=사회복지사)
    license_no: str     # 면허번호 (X(100) 공간에 실 번호만 기록, 나머지 공백)
    change_date: str = ""              # 변경일 X(8) (미입력 시 공백)
    prescription_days: int = 0         # 처방일수 9(3)
    copay_rate_code: str = "D"         # 본인부담률구분코드 X(2)
    prescription_issue_date: str = ""  # 처방전발급일자 9(8) (미입력 시 0)
    prescription_serial: int = 0       # 처방전일련번호 9(5)
    adjustment_type: str = ""          # 가감등구분 X(10)


def build_procedure_record(p: ProcedureDetail) -> str:
    """C2-13 명세서진료내역(의치과및한방) 레코드 생성 (data 291 bytes + CRLF = Max 293).

    의치과·한방 전용 (수록사양 U1). 코드 영역 X(9)를 코드구분 X(1) + 코드 X(8)로 분할 사용.

    레이아웃:
      1-  17: KEY
     18-  21: 공란 X(4)
     22-  23: 항번호 XX
     24-  25: 목번호 99
     26      : 코드구분 X(1)
     27-  34: 코드 X(8)
     35-  40: 공란 X(6)
     41-  50: 단가 9(9)V9 (10 chars)
     51-  58: 1회투약량/실시횟수 9(4)V9999 (8 chars)
     59-  64: 일투 9(4)V99 — qty 기준 1일 횟수 (6 chars)
     65-  67: 총투여일수/실시횟수 9(3)
     68-  77: 금액 9(10)
     78-  85: 변경일 X(8)
     86-  98: 공란 X(13)
     99- 101: 처방일수 9(3)
    102- 103: 본인부담률구분코드 X(2)
    104- 111: 처방전발급일자 9(8)
    112- 116: 처방전일련번호 9(5)
    117- 148: 치식사항 4×X(8)=32 (한방은 공란)
    149- 158: 가감등구분 X(10)
    159- 168: 공란 X(10)
    169- 178: 공란 X(10)
    179- 187: 공란 X(9)
    188      : 면허종류 X(1)
    189- 288: 면허번호 X(100)
    289- 291: 공란 X(3)
    """
    parts = [
        *_key_parts(p.key),                                                   # 1-17
        _fmtx("", 4),                                                         # 18-21  공란
        _fmtx(p.hang, 2),                                                     # 22-23  항번호
        _fmtx(p.mok, 2),                                                      # 24-25  목번호
        _fmtx(p.code_gubun, 1),                                               # 26     코드구분
        _fmtx(p.code, 8),                                                     # 27-34  코드
        _fmtx("", 6),                                                         # 35-40  공란
        _fmt9v9(p.unit_price, 9, 1),                                          # 41-50  단가
        _fmt9v9(p.qty, 4, 4),                                                 # 51-58  1회투약량
        _fmt9v9(p.qty, 4, 2),                                                 # 59-64  일투 (qty 재사용)
        _fmt9(p.days, 3),                                                     # 65-67  총투여일수
        _fmt9(p.amount, 10),                                                  # 68-77  금액
        _fmtx(p.change_date, 8),                                              # 78-85  변경일
        _fmtx("", 13),                                                        # 86-98  공란
        _fmt9(p.prescription_days, 3),                                        # 99-101 처방일수
        _fmtx(p.copay_rate_code, 2),                                          # 102-103 본인부담률구분코드
        _fmt9(int(p.prescription_issue_date) if p.prescription_issue_date else 0, 8),  # 104-111 처방전발급일자
        _fmt9(p.prescription_serial, 5),                                      # 112-116 처방전일련번호
        _fmtx("", 32),                                                        # 117-148 치식사항 (한방은 공란)
        _fmtx(p.adjustment_type, 10),                                         # 149-158 가감등구분
        _fmtx("", 10),                                                        # 159-168 공란
        _fmtx("", 10),                                                        # 169-178 공란
        _fmtx("", 9),                                                         # 179-187 공란
        _fmtx(p.license_type, 1),                                             # 188    면허종류
        _fmtx(p.license_no, 100),                                             # 189-288 면허번호
        _fmtx("", 3),                                                         # 289-291 공란
    ]
    return _build(parts, 291)


def build_eof_record(key: RecordKey) -> str:
    """C2-09 EOF 레코드 생성 (20 bytes + CRLF)."""
    parts = [
        *_key_parts(key),   # 1-17
        _fmtx("", 3),       # 공란
    ]
    return _build(parts, 20)


# ---------------------------------------------------------------------------
# EDI 파일 조립
# ---------------------------------------------------------------------------

@dataclass
class EDIFile:
    """완성된 EDI 파일을 구성하는 레코드 목록."""
    header: ClaimHeader
    patient_records: list[PatientRecord] = field(default_factory=list)
    diagnosis_records: list[tuple[int, DiagnosisRecord]] = field(default_factory=list)
    procedure_records: list[tuple[int, ProcedureDetail]] = field(default_factory=list)
    special_records: list[tuple[int, SpecialRecord]] = field(default_factory=list)


def generate_edi(edi: EDIFile) -> bytes:
    """EDI 파일 전체를 EUC-KR 바이트로 생성한다."""
    lines: list[str] = []

    lines.append(build_claim_header(edi.header))

    for patient in edi.patient_records:
        lines.append(build_patient_record(patient))

        for serial, diag in edi.diagnosis_records:
            if serial == patient.key.serial_no:
                lines.append(build_diagnosis_record(diag))

        for serial, proc in edi.procedure_records:
            if serial == patient.key.serial_no:
                lines.append(build_procedure_record(proc))

        for serial, special in edi.special_records:
            if serial == patient.key.serial_no:
                lines.append(build_special_record(special))

    lines.append(build_eof_record(edi.header.key))

    return "".join(lines).encode("euc-kr", errors="replace")
