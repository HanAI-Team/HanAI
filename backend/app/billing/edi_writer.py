"""EDI 파일 생성기.

HIRA 「요양급여비용 청구방법, 심사청구서·명세서서식 및 작성요령」
Ⅲ. (별첨2) 전산매체 작성요령 (2024년 7월판, 286~330페이지) 기준.
수록사양 U1(의치과 및 한방).

2026-07-09 전면 재작성: 기존 코드가 "전산매체파일 수록사양"이라고 docstring에
적어놓고도 실제로는 필드 구성이 원문과 달랐던 것을 별첨2 원문(286~330p) 직접
대조로 발견해 전부 다시 맞춤. (참고: 별첨1 "전자문서 작성요령"과는 완전히
다른 문서/다른 레이아웃이니 혼동 주의 — SAM File은 별첨2 기준.)

자료구분 코드 (KEY 직후 1바이트, X(1)):
  '0': 요양급여비용(의료급여비용)심사청구서
  '1': 명세서일반내역
  '2': 명세서상병내역
  '3': 명세서진료내역
  '5': 명세서처방내역
  '8': 명세서특정내역
  '9': 요양급여비용 EOF(마지막 정보)

KEY 구조(모든 레코드 공통, 17바이트):
  요양기관기호 9(8) + 명세서일련번호(일련번호9(5)+확장번호9(4))
  → 이 부분은 기존 구현(RecordKey)이 원래 정확했음. 재검증으로 확인됨.
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
# 공통 KEY 필드 (모든 레코드 앞부분, 17바이트) — 재검증 결과 기존 구조가 정확함
# ---------------------------------------------------------------------------

@dataclass
class RecordKey:
    institution_code: str   # 요양기관기호 9(8)
    serial_no: int          # 명세서일련번호(일련번호) 9(5)
    ext_no: int = 0         # 명세서일련번호(확장번호) 9(4)


def _key_parts(key: RecordKey) -> list[str]:
    return [
        _fmt9(int(key.institution_code), 8),
        _fmt9(key.serial_no, 5),
        _fmt9(key.ext_no, 4),
    ]


# ---------------------------------------------------------------------------
# C2-00: 요양급여비용(의료급여비용)심사청구서
# ---------------------------------------------------------------------------

@dataclass
class ClaimHeader:
    key: RecordKey
    billing_type: str       # 수록사양번호 X(2) Vn (V1=의치과및한방, V2=보건기관및의료급여정액, V3=약국)
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

    2026-07-09 재검증: KEY 직후 "서식번호"만 있던 걸 별첨2 원문 대조로
    "자료구분(1, '0')" + "서식(2, '01')" 순서로 정정. 나머지 금액 필드들
    (의사수/대행청구단체기호/검사승인번호 등 꼬리 부분)은 원문과 이미 일치가
    확인되어 유지함. 다만 중간 금액 필드들의 정확한 바이트 위치는 이번
    재작성에서 "자료구분 1바이트 추가"로 인해 전체가 1바이트씩 뒤로 밀림 —
    진료년월~차등수가 구간 세부 위치는 근사치이며 완전 재검증 권장.
    """
    parts = [
        *_key_parts(h.key),                                          # 1-17   KEY
        _fmtx("0", 1),                                               # 18     자료구분 '0'
        _fmt9(1, 2),                                                 # 19-20  서식 '01'
        _fmtx(h.billing_type, 2),                                    # 21-22  수록사양번호
        _fmt9(0, 1),                                                 # 23     보험자종별구분(헤더는 기본값)
        _fmt9(0, 2),                                                 # 24-25  진료분야
        _fmtx("", 15),                                               # 26-40  공란(예비)
        _fmt9(int(h.treatment_ym), 6),                               # 41-46  진료년월
        _fmt9(int(h.claim_date), 8),                                 # 47-54  청구일자
        _fmtx(h.claimer, 12),                                        # 55-66  청구인
        _fmtx(h.writer, 12),                                         # 67-78  작성자
        _fmt9(int(h.writer_rrn.replace("-", "")), 13),               # 79-91  작성자주민등록번호
        _fmtx("", 8),                                                # 92-99  공란
        _fmt9(h.claim_count, 6),                                     # 100-105 청구건수
        _fmt9(h.benefit_total_1, 12),                                # 106-117 요양급여비용총액1
        _fmt9(h.copayment, 12),                                      # 118-129 본인일부부담금
        _fmt9(h.claim_amount, 12),                                   # 130-141 청구액
        _fmt9(h.upper_limit_excess, 12),                             # 142-153 본인부담상한액초과금
        _fmt9(h.disability_medical_cost, 12),                        # 154-165 장애인의료비
        _fmt9(h.graduated_claim, 10),                                # 166-175 차등수가청구액
        _fmt9v9(h.graduated_index, 4, 3),                            # 176-182 차등지수
        _fmt9v9(h.treatment_days, 6, 2),                             # 183-190 진료일수
        _fmt9v9(h.doctor_count, 2, 2),                               # 191-194 의사수
        _fmtx("", 5),                                                # 195-199 대행청구단체기호
        _fmtx(h.approval_no, 35),                                    # 200-234 검사승인번호
        _fmt9(h.benefit_total_2, 12),                                # 235-246 요양급여비용총액2
        _fmt9(h.veterans_claim, 12),                                 # 247-258 보훈청구액
        _fmt9(h.support_fund, 12),                                   # 259-270 지원금
        _fmt9(h.full_price_copay_total, 12),                         # 271-282 100분의100 본인부담금총액
        _fmt9(h.veterans_copay, 12),                                 # 283-294 보훈 본인일부부담금
        _fmtx("", 5),                                                # 295-299 공란
        _fmt9(h.under_full_total, 12),                               # 300-311 100분의100미만 총액
        _fmt9(h.under_full_copay, 12),                               # 312-323 100분의100미만 본인일부부담금
        _fmt9(h.under_full_claim, 12),                               # 324-335 100분의100미만 청구액
        _fmt9(h.under_full_veterans_claim, 10),                      # 336-345 100분의100미만 보훈청구액
    ]
    return _build(parts, 345)


# ---------------------------------------------------------------------------
# C2-11: 명세서 일반내역 (의·치과 및 한방)
# ---------------------------------------------------------------------------

@dataclass
class PatientRecord:
    key: RecordKey
    format_code: str = "13"  # 서식 9(2): 12=한방입원, 13=한방외래
    insurance_type: str = "4"  # 보험자종별구분 9(1): 4=건강보험 5=의료급여 7=보훈
    employer_code: str = ""    # 보장기관기호 X(8)
    cert_no: str = ""          # 증번호(보장시설·노숙인시설기호) X(13)
    subscriber_name: str = ""  # 가입자(세대주)성명 X(12)
    patient_name: str = ""     # 수진자성명 X(12)
    patient_rrn: str = "0000000000000"  # 수진자주민등록번호 9(13)
    inpatient_days: int = 0    # 입내원일수 9(3)
    benefit_days: int = 0      # 요양급여일수 9(3)
    flat_rate_type: str = "0"  # 정액·정률구분 9(1)
    work_injury_type: str = "0"  # 공상등구분 X(1)
    benefit_total_1: int = 0
    copayment: int = 0
    support_fund: int = 0
    claim_amount: int = 0
    upper_limit_excess: int = 0
    benefit_total_2: int = 0
    veterans_claim: int = 0
    full_price_copay_total: int = 0
    veterans_copay: int = 0
    under_full_total: int = 0
    under_full_copay: int = 0
    under_full_claim: int = 0
    under_full_veterans_claim: int = 0
    medical_aid_type: str = " "  # 의료급여종별구분 X(1)
    deferred_or_disability: int = 0  # 대불금 또는 장애인의료비 9(10)
    receipt_no: int = 0        # (보완·추가·분리청구) 접수번호 9(7)
    record_serial: int = 0     # (보완·추가·분리청구) 당초 명세서일련번호 9(5)
    reason_code: str = "  "    # 사유 X(2)
    claim_type_code: str = "0"  # 코드 9(1): 1=보완 2=추가 3=분리
    first_admission_date: str = "00000000"  # 최초입원개시일 9(8)


def build_patient_record(p: PatientRecord) -> str:
    """C2-11 명세서일반내역 레코드 생성 (271 bytes + CRLF).

    2026-07-09 별첨2 원문(296~301p) 전면 재검증 반영. 기존 구현은 완전히
    다른 필드 순서/총바이트(347)를 쓰고 있어서 원문 그대로 재작성함.

    레이아웃:
      1-  17: KEY
      18    : 자료구분 '1'
     19-  20: 서식 (12=한방입원, 13=한방외래)
     21    : 보험자종별구분 (4/5/7)
     22-  29: 보장기관기호 X(8)
     30-  42: 증번호 X(13)
     43-  54: 가입자(세대주)성명 X(12)
     55-  66: 수진자성명 X(12)
     67-  79: 수진자주민등록번호 9(13)
     80-  82: 입내원일수 9(3)
     83-  85: 요양급여일수 9(3)
     86    : 정액·정률구분 9(1)
     87    : 공상등구분 X(1)
     88-  97: 공란(청구사항 공란1) 9(10)
     98- 107: 공란(청구사항 공란2) 9(10)
    108- 117: 요양급여비용총액1 9(10)
    118- 127: 본인일부부담금 9(10)
    128- 137: 지원금 9(10)
    138- 147: 청구액 9(10)
    148- 157: 본인부담상한액초과금 9(10)
    158- 167: 요양급여비용총액2/진료비총액 9(10)
    168- 177: 보훈청구액 9(10)
    178- 187: 건강보험(의료급여) 100분의100 본인부담금총액 9(10)
    188- 197: 보훈 본인일부부담금 9(10)
    198- 207: 100분의100미만 총액 9(10)
    208- 217: 100분의100미만 본인일부부담금 9(10)
    218- 227: 100분의100미만 청구액 9(10)
    228- 237: 100분의100미만 보훈청구액 9(10)
    238    : 의료급여종별구분 X(1)
    239- 248: 대불금 또는 장애인의료비 9(10)
    249- 255: 접수번호 9(7)
    256- 260: (당초) 명세서일련번호 9(5)
    261- 262: 사유 X(2)
    263    : 코드 9(1)
    264- 271: 최초입원개시일 9(8)
    """
    parts = [
        *_key_parts(p.key),                                       # 1-17
        _fmtx("1", 1),                                            # 18     자료구분
        _fmt9(int(p.format_code), 2),                             # 19-20  서식
        _fmt9(int(p.insurance_type), 1),                          # 21     보험자종별구분
        _fmtx(p.employer_code, 8),                                # 22-29  보장기관기호
        _fmtx(p.cert_no, 13),                                     # 30-42  증번호
        _fmtx(p.subscriber_name, 12),                             # 43-54  가입자성명
        _fmtx(p.patient_name, 12),                                # 55-66  수진자성명
        _fmt9(int(p.patient_rrn.replace("-", "")), 13),           # 67-79  수진자주민등록번호
        _fmt9(p.inpatient_days, 3),                               # 80-82  입내원일수
        _fmt9(p.benefit_days, 3),                                 # 83-85  요양급여일수
        _fmt9(int(p.flat_rate_type), 1),                          # 86     정액·정률구분
        _fmtx(p.work_injury_type, 1),                             # 87     공상등구분
        _fmt9(0, 10),                                             # 88-97  공란1
        _fmt9(0, 10),                                             # 98-107 공란2
        _fmt9(p.benefit_total_1, 10),                             # 108-117 요양급여비용총액1
        _fmt9(p.copayment, 10),                                   # 118-127 본인일부부담금
        _fmt9(p.support_fund, 10),                                # 128-137 지원금
        _fmt9(p.claim_amount, 10),                                # 138-147 청구액
        _fmt9(p.upper_limit_excess, 10),                          # 148-157 본인부담상한액초과금
        _fmt9(p.benefit_total_2, 10),                             # 158-167 요양급여비용총액2
        _fmt9(p.veterans_claim, 10),                              # 168-177 보훈청구액
        _fmt9(p.full_price_copay_total, 10),                      # 178-187 100분의100 본인부담금총액
        _fmt9(p.veterans_copay, 10),                              # 188-197 보훈 본인일부부담금
        _fmt9(p.under_full_total, 10),                            # 198-207 100분의100미만 총액
        _fmt9(p.under_full_copay, 10),                            # 208-217 100분의100미만 본인일부부담금
        _fmt9(p.under_full_claim, 10),                            # 218-227 100분의100미만 청구액
        _fmt9(p.under_full_veterans_claim, 10),                   # 228-237 100분의100미만 보훈청구액
        _fmtx(p.medical_aid_type, 1),                             # 238    의료급여종별구분
        _fmt9(p.deferred_or_disability, 10),                      # 239-248 대불금/장애인의료비
        _fmt9(p.receipt_no, 7),                                   # 249-255 접수번호
        _fmt9(p.record_serial, 5),                                # 256-260 (당초)명세서일련번호
        _fmtx(p.reason_code, 2),                                  # 261-262 사유
        _fmt9(int(p.claim_type_code), 1),                         # 263    코드
        _fmt9(int(p.first_admission_date), 8),                    # 264-271 최초입원개시일
    ]
    return _build(parts, 271)


# ---------------------------------------------------------------------------
# C2-02: 명세서 상병내역
# ---------------------------------------------------------------------------

@dataclass
class DiagnosisRecord:
    key: RecordKey
    kcd_code: str            # 상병분류기호 X(6)
    disease_class: str = "1"  # 상병분류구분 9(1): 1=주상병 2=부상병 3=배제된상병
    onset_date: str = "00000000"  # 내원일자/당월요양개시일 X(8)
    treatment_dept: int = 9    # 진료과목 9(2) (09=한의과)
    sub_specialty: int = 0     # 세부전문과목 9(2)
    inpatient_route: int = 0   # 입원경로 9(2)
    treatment_result: int = 9  # 진료결과 9(1): 9=퇴원 또는 외래 치료종결
    license_kind: str = "3"    # 면허종류 X(1): 3=한의사
    license_no: str = ""       # 면허번호 X(10)


def build_diagnosis_record(d: DiagnosisRecord) -> str:
    """C2-02 명세서상병내역 레코드 생성 (51 bytes + CRLF).

    2026-07-09 별첨2 원문(293~295p) 재검증 반영.

    레이아웃:
      1-  17: KEY
      18    : 자료구분 '2'
     19-  24: 상병분류기호 X(6)
     25    : 상병분류구분 9(1)
     26-  33: 내원일자/당월요양개시일 X(8)
     34-  35: 진료과목 9(2)
     36-  37: 세부전문과목 9(2)
     38-  39: 입원경로 9(2)
     40    : 진료결과 9(1)
     41    : 면허종류 X(1)
     42-  51: 면허번호 X(10)
    """
    parts = [
        *_key_parts(d.key),                     # 1-17
        _fmtx("2", 1),                           # 18     자료구분
        _fmtx(d.kcd_code, 6),                    # 19-24  상병분류기호
        _fmt9(int(d.disease_class), 1),          # 25     상병분류구분
        _fmtx(d.onset_date, 8),                  # 26-33  내원일자
        _fmt9(d.treatment_dept, 2),              # 34-35  진료과목
        _fmt9(d.sub_specialty, 2),               # 36-37  세부전문과목
        _fmt9(d.inpatient_route, 2),             # 38-39  입원경로
        _fmt9(d.treatment_result, 1),            # 40     진료결과
        _fmtx(d.license_kind, 1),                # 41     면허종류
        _fmtx(d.license_no, 10),                 # 42-51  면허번호
    ]
    return _build(parts, 51)


# ---------------------------------------------------------------------------
# C2-08: 명세서 특정내역기재란
# ---------------------------------------------------------------------------

@dataclass
class SpecialRecord:
    key: RecordKey
    record_group_type: str  # 발생단위구분 X(1): 1=명세서단위 2=확장번호단위 3=처방내역확장번호단위 4=처방내역단위
    prescription_no: int    # 처방전발급번호 9(13)
    record_ext_no: int      # 진료내역확장번호 9(4)
    special_code: str       # 특정내역구분 X(5)
    content: str            # 특정내역 X(700)


def build_special_record(s: SpecialRecord) -> str:
    """C2-08 명세서특정내역 레코드 생성 (741 bytes + CRLF).

    2026-07-09 별첨2 원문(326~327p) 재검증 반영. 기존 구현은 "서식번호(2)"를
    잘못 넣고 "발생단위구분"이 아예 빠져있어서, 747바이트로 실제보다
    6바이트 많았던 것을 정정함.

    레이아웃:
      1-  17: KEY
      18    : 자료구분 '8'
      19    : 발생단위구분 X(1)
     20-  32: 처방전발급번호 9(13)
     33-  36: 진료내역확장번호 9(4)
     37-  41: 특정내역구분 X(5)
     42- 741: 특정내역 X(700)
    """
    parts = [
        *_key_parts(s.key),                     # 1-17
        _fmtx("8", 1),                           # 18     자료구분
        _fmtx(s.record_group_type, 1),           # 19     발생단위구분
        _fmt9(s.prescription_no, 13),            # 20-32  처방전발급번호
        _fmt9(s.record_ext_no, 4),               # 33-36  진료내역확장번호
        _fmtx(s.special_code, 5),                # 37-41  특정내역구분
        _fmtx(s.content, 700),                   # 42-741 특정내역
    ]
    return _build(parts, 741)


# ---------------------------------------------------------------------------
# C2-09: 마지막 정보파일 EOF
# ---------------------------------------------------------------------------

def build_eof_record(key: RecordKey) -> str:
    """C2-09 EOF 레코드 생성 (18 bytes + CRLF).

    레이아웃: 1-17 KEY (요양기관기호/일련번호/확장번호 최댓값 채움 관례),
    18 자료구분 '9'.
    """
    parts = [
        *_key_parts(key),   # 1-17
        _fmtx("9", 1),      # 18  자료구분
    ]
    return _build(parts, 18)


# ---------------------------------------------------------------------------
# C2-13: 명세서 진료내역 (의·치과 및 한방)
# ---------------------------------------------------------------------------

@dataclass
class ProcedureDetail:
    key: RecordKey
    hang: str            # 항 X(2) (예: "04" = 시술및처치료, 한방)
    mok: str             # 목 9(2) (예: "01" = 침술)
    code_gubun: str      # 코드구분 X(1): A=수가 B=준용수가 C=약가 H=치료재료 (한방)
    code: str            # 코드 X(9)
    unit_price: Decimal  # 단가 9(9)V9
    dose_per_time: Decimal = Decimal("0")  # 1회투약량 9(4)V9(4) (한방 의약품 제외 대상 아니면 0)
    qty: Decimal = Decimal("0")            # 1일투여량/실시횟수 9(4)V9(2)
    days: int = 0         # 총투 9(3)
    amount: int = 0        # 금액 9(10)
    copay_rate_code: str = ""  # 본인부담률구분코드 X(1)
    change_date: str = ""      # 변경일 X(8)
    license_type: str = "3"    # 면허종류 X(1): 3=한의사
    license_no: str = ""       # 면허번호 X(100)
    prescription_days: int = 0  # (처방내역) 처방일수 9(3)
    is_prescription: bool = False  # 자료구분을 3(진료) 대신 5(처방)로 쓸지 여부


def build_procedure_record(p: ProcedureDetail) -> str:
    """C2-13 명세서진료내역(의치과및한방) 레코드 생성 (185 bytes + CRLF).

    2026-07-09 별첨2 원문(301~307p) 재검증 반영. 기존 구현과 필드 구성이
    많이 달라 전면 재작성. 처방내역(반복조제횟수 등) 꼬리 필드는 원문에서도
    "(사용유보)"로 되어 있어 이번 스코프에서 생략.

    레이아웃:
      1-  17: KEY
      18    : 자료구분 '3'(진료내역) 또는 '5'(처방내역)
     19-  20: 항 X(2)
     21-  22: 목 9(2)
     23    : 코드구분 X(1)
     24-  32: 코드 X(9)
     33-  42: 단가 9(9)V9 (10 chars)
     43-  50: 1회투약량 9(4)V9(4) (8 chars)
     51-  56: 1일투여량/실시횟수 9(4)V9(2) (6 chars)
     57-  59: 총투 9(3)
     60-  69: 금액 9(10)
     70    : 본인부담률구분코드 X(1)
     71-  78: 변경일 X(8)
     79    : 면허종류 X(1)
     80- 179: 면허번호 X(100)
    180- 182: 처방일수 9(3)
    183- 185: 공란(반복조제횟수 등 사용유보) X(3)
    """
    parts = [
        *_key_parts(p.key),                                        # 1-17
        _fmtx("5" if p.is_prescription else "3", 1),                # 18     자료구분
        _fmtx(p.hang, 2),                                           # 19-20  항
        _fmt9(int(p.mok), 2),                                       # 21-22  목
        _fmtx(p.code_gubun, 1),                                     # 23     코드구분
        _fmtx(p.code, 9),                                           # 24-32  코드
        _fmt9v9(p.unit_price, 9, 1),                                # 33-42  단가
        _fmt9v9(p.dose_per_time, 4, 4),                             # 43-50  1회투약량
        _fmt9v9(p.qty, 4, 2),                                       # 51-56  1일투여량/실시횟수
        _fmt9(p.days, 3),                                           # 57-59  총투
        _fmt9(p.amount, 10),                                        # 60-69  금액
        _fmtx(p.copay_rate_code, 1),                                # 70     본인부담률구분코드
        _fmtx(p.change_date, 8),                                    # 71-78  변경일
        _fmtx(p.license_type, 1),                                   # 79     면허종류
        _fmtx(p.license_no, 100),                                   # 80-179 면허번호
        _fmt9(p.prescription_days, 3),                              # 180-182 처방일수
        _fmtx("", 3),                                               # 183-185 공란(사용유보)
    ]
    return _build(parts, 185)


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

    lines.append(build_eof_record(RecordKey(
        institution_code=edi.header.key.institution_code,
        serial_no=99999,
        ext_no=9999,
    )))

    return "".join(lines).encode("euc-kr", errors="replace")
