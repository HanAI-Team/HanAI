"""EDI(SAM) 파일 생성기.

HIRA 「요양급여비용 청구방법, 심사청구서·명세서서식 및 작성요령」
Ⅱ. (별첨1) 전자문서 교환방식(EDI) 작성요령 기준.

2026-07-09 전면 재작성: 기존 코드가 별첨2(전산매체 작성요령) 레이아웃으로
구현돼 있었으나, MCPoS 상시점검 프로그램이 요구하는 "SAM(EDI) 파일"은
별첨1(전자문서 교환방식) 레이아웃임을 확인해 전부 다시 맞춤. 별첨1과 별첨2는
같은 원문서(848p) 안에 있는 완전히 다른 챕터/레이아웃이므로 혼동 주의.

레코드 구성:
  레코드 1  (헤더)    : 요양급여비용(의료급여비용) 심사청구서 — 서식번호 H010/H011
  레코드 2  (일반내역) : 한방 명세서 일반내역 — 서식번호 K020/K021/K030/K031
  레코드 2-1(상병내역) : 한방 명세서 상병내역 (KCD 진단코드)
  레코드 3  (진료내역) : 한방 명세서 진료내역
  레코드 4  (특정내역) : 명세서 특정내역기재란 (공통, JS011 경혈코드 등)

레코드 2/2-1/3/4는 모두 청구번호 an(10) + 명세서일련번호 an(5)로 시작한다
(RecordKey, 15바이트). 헤더(레코드 1)만 그 앞에 청구서서식버전(3)+
명세서서식버전(3)이 추가로 붙고, 명세서일련번호 없이 청구번호만 갖는다.
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
# 공통 KEY (레코드 2/2-1/3/4 앞부분, 15바이트: 청구번호10+명세서일련번호5)
# ---------------------------------------------------------------------------

@dataclass
class RecordKey:
    claim_no: str        # 청구번호 an(10): CCYYMM(6)+일련번호(4)
    record_serial: int   # 명세서일련번호 an(5): 00001부터 순차


def _key_parts(key: RecordKey) -> list[str]:
    return [
        _fmtx(key.claim_no, 10),
        _fmt9(key.record_serial, 5),
    ]


# ---------------------------------------------------------------------------
# 레코드 1: 요양급여비용(의료급여비용) 심사청구서 (청구서 헤더)
# ---------------------------------------------------------------------------

@dataclass
class ClaimHeader:
    claim_no: str                 # 청구번호 an(10)
    form_no: str                  # 서식번호 an(4): H010=건강보험, H011=의료급여
    institution_code: str         # 요양기관기호 an(8)
    insurance_type_code: str = "4"  # 보험자종별구분 an(1): 건강보험4 보훈7 의료급여1차1·2차2
    claim_type_code: str = " "      # 청구구분 an(1): 공백(신규)/보완1/추가2
    treatment_ym: str = ""          # 진료년월 an(6) CCYYMM
    claim_count: int = 0            # 건수 n(6)
    benefit_total_1: int = 0
    copayment: int = 0
    upper_limit_excess: int = 0
    claim_amount: int = 0
    support_fund: int = 0
    disability_medical_cost: int = 0
    benefit_total_2: int = 0
    veterans_claim: int = 0
    full_price_copay_total: int = 0
    veterans_copay: int = 0
    under_full_total: int = 0
    under_full_copay: int = 0
    under_full_claim: int = 0
    under_full_veterans_claim: int = 0
    graduated_days: Decimal = Decimal("0")           # 차등수가 진료(조제)일수 n(4.2)
    graduated_doctor_count: Decimal = Decimal("0")   # 차등수가 의사(약사)수 n(2.2) 사용유보
    graduated_index: Decimal = Decimal("0")          # 차등지수 n(1.7)
    graduated_claim: int = 0                         # 차등수가청구액 n(12)
    claim_date: str = ""              # 청구일자 an(8) CCYYMMDD
    claimer: str = ""                 # 청구인 an(20)
    writer: str = ""                  # 작성자성명 an(20)
    writer_birth: str = "0000000000000"  # 작성자생년월일 an(13) — 형식 미확정, 플레이스홀더
    approval_no: str = ""             # 검사승인번호 an(35)


def build_claim_header(h: ClaimHeader) -> str:
    """레코드 1 생성 (2096 bytes + CRLF)."""
    parts = [
        _fmtx("091", 3),                          # 1-3     청구서서식버전
        _fmtx("091", 3),                          # 4-6     명세서서식버전
        _fmtx(h.claim_no, 10),                    # 7-16    청구번호
        _fmtx(h.form_no, 4),                      # 17-20   서식번호
        _fmt9(int(h.institution_code), 8),        # 21-28   요양기관기호
        _fmt9(1, 1),                              # 29      수신기관
        _fmtx(h.insurance_type_code, 1),          # 30      보험자종별구분
        _fmtx(h.claim_type_code, 1),              # 31      청구구분
        _fmt9(0, 1),                              # 32      청구단위구분(월단위 통합청구)
        _fmt9(9, 1),                              # 33      진료구분(한방)
        _fmt9(9, 1),                              # 34      진료분야구분(한의과)
        _fmt9(9, 1),                              # 35      진료형태(한방외래)
        _fmt9(int(h.treatment_ym), 6),            # 36-41   진료년월
        _fmt9(h.claim_count, 6),                  # 42-47   건수
        _fmt9(h.benefit_total_1, 12),             # 48-59   요양급여비용총액1
        _fmt9(h.copayment, 12),                   # 60-71   본인일부부담금
        _fmt9(h.upper_limit_excess, 12),          # 72-83   본인부담상한액초과금총액
        _fmt9(h.claim_amount, 12),                # 84-95   청구액
        _fmt9(h.support_fund, 12),                # 96-107  지원금
        _fmt9(h.disability_medical_cost, 12),     # 108-119 장애인의료비
        _fmt9(h.benefit_total_2, 12),             # 120-131 요양급여비용총액2·진료비총액
        _fmt9(h.veterans_claim, 12),               # 132-143 보훈청구액
        _fmt9(h.full_price_copay_total, 12),       # 144-155 건강보험(의료급여)100/100본인부담금총액
        _fmt9(h.veterans_copay, 12),               # 156-167 보훈본인일부부담금
        _fmt9(h.under_full_total, 12),             # 168-179 100분의100미만총액
        _fmt9(h.under_full_copay, 12),             # 180-191 100분의100미만본인일부부담금
        _fmt9(h.under_full_claim, 12),              # 192-203 100분의100미만청구액
        _fmt9(h.under_full_veterans_claim, 12),     # 204-215 100분의100미만보훈청구액
        _fmt9v9(h.graduated_days, 4, 2),            # 216-221 차등수가 진료(조제)일수
        _fmt9v9(h.graduated_doctor_count, 2, 2),    # 222-225 차등수가 의사(약사)수(사용유보)
        _fmt9v9(h.graduated_index, 1, 7),           # 226-233 차등지수
        _fmt9(h.graduated_claim, 12),                # 234-245 차등수가청구액
        _fmt9(int(h.claim_date), 8),                 # 246-253 청구일자
        _fmtx(h.claimer, 20),                        # 254-273 청구인
        _fmtx(h.writer, 20),                          # 274-293 작성자성명
        _fmt9(int(h.writer_birth), 13),               # 294-306 작성자생년월일
        _fmtx(h.approval_no, 35),                     # 307-341 검사승인번호
        _fmtx("", 5),                                 # 342-346 대행청구단체기호
        _fmtx("", 1750),                              # 347-2096 참조란
    ]
    return _build(parts, 2096)


# ---------------------------------------------------------------------------
# 레코드 2: 한방 명세서 일반내역
# ---------------------------------------------------------------------------

@dataclass
class PatientRecord:
    key: RecordKey
    form_no: str = "K021"           # 서식번호 an(4): K020=건강보험한방입원 K021=건강보험한방외래
                                    #                 K030=의료급여한방입원 K031=의료급여한방외래
    institution_code: str = ""     # 요양기관기호 an(8)
    employer_code: str = ""        # 보장기관기호 an(11) (의료급여 수급권자 관할 시군구, 건강보험은 공란)
    medical_aid_type: str = " "    # 의료급여종별구분 an(1): 1종/2종/행려 등
    work_injury_type: str = "0"    # 공상등구분 an(1)
    flat_rate_type: str = " "      # 정액·정률구분 an(1) (2007.7.31 이전 진료분만 해당)
    claim_type_code: str = "0"     # 청구구분코드 an(1): 보완1 추가2 분리3
    receipt_no: int = 0            # 접수번호 an(7) (보완/추가/분리청구 시만)
    record_serial: int = 0         # 명세서일련번호(원청구) an(5)
    reason_code: str = "  "        # 사유코드 an(2) (보완청구 시)
    first_admission_date: str = "00000000"  # 최초입원개시일 an(8) (분리청구 시)
    subscriber_name: str = ""      # 가입자(세대주)성명 an(20)
    cert_no: str = ""              # 증번호 an(20)
    patient_name: str = ""         # 수진자성명 an(20)
    patient_rrn: str = "0000000000000"  # 수진자주민등록번호 an(13)
    benefit_days: int = 0           # 요양급여일수 n(3)
    inpatient_days: int = 0         # 입원일수/총내원일수 n(3)
    treatment_result: str = "9"    # 진료결과 an(1): 계속1 이송2 회송3 사망4 퇴원/치료종결9
    benefit_total_1: int = 0
    copayment: int = 0
    upper_limit_excess: int = 0
    claim_amount: int = 0
    support_fund: int = 0
    disability_medical_cost: int = 0  # 장애인의료비 n(10)
    deferred_payment: int = 0         # 대불금 n(10)
    benefit_total_2: int = 0
    veterans_claim: int = 0
    full_price_copay_total: int = 0
    veterans_copay: int = 0
    under_full_total: int = 0
    under_full_copay: int = 0
    under_full_claim: int = 0
    under_full_veterans_claim: int = 0


def build_patient_record(p: PatientRecord) -> str:
    """레코드 2 생성 (325 bytes + CRLF)."""
    parts = [
        *_key_parts(p.key),                                  # 1-15   청구번호+명세서일련번호
        _fmtx(p.form_no, 4),                                 # 16-19  서식번호
        _fmt9(int(p.institution_code), 8),                   # 20-27  요양기관기호
        _fmtx(p.employer_code, 11),                          # 28-38  보장기관기호
        _fmtx(p.medical_aid_type, 1),                        # 39     의료급여종별구분
        _fmtx(p.work_injury_type, 1),                        # 40     공상등구분
        _fmtx(p.flat_rate_type, 1),                          # 41     정액·정률구분
        _fmtx(p.claim_type_code, 1),                         # 42     청구구분코드
        _fmt9(p.receipt_no, 7),                              # 43-49  접수번호
        _fmt9(p.record_serial, 5),                           # 50-54  명세서일련번호(원청구)
        _fmtx(p.reason_code, 2),                             # 55-56  사유코드
        _fmt9(int(p.first_admission_date), 8),               # 57-64  최초입원개시일
        _fmtx(p.subscriber_name, 20),                        # 65-84  가입자(세대주)성명
        _fmtx(p.cert_no, 20),                                # 85-104 증번호
        _fmtx(p.patient_name, 20),                           # 105-124 수진자성명
        _fmt9(int(p.patient_rrn.replace("-", "")), 13),      # 125-137 수진자주민등록번호
        _fmt9(p.benefit_days, 3),                            # 138-140 요양급여일수
        _fmt9(p.inpatient_days, 3),                          # 141-143 입원일수/총내원일수
        _fmtx("", 31),                                       # 144-174 공란
        _fmtx(p.treatment_result, 1),                        # 175    진료결과
        _fmt9(p.benefit_total_1, 10),                        # 176-185 요양급여비용총액1
        _fmt9(p.copayment, 10),                              # 186-195 본인일부부담금
        _fmt9(p.upper_limit_excess, 10),                     # 196-205 본인부담상한액초과금
        _fmt9(p.claim_amount, 10),                           # 206-215 청구액
        _fmt9(p.support_fund, 10),                           # 216-225 지원금
        _fmt9(p.disability_medical_cost, 10),                # 226-235 장애인의료비
        _fmt9(p.deferred_payment, 10),                       # 236-245 대불금
        _fmt9(p.benefit_total_2, 10),                        # 246-255 요양급여비용총액2·진료비총액
        _fmt9(p.veterans_claim, 10),                         # 256-265 보훈청구액
        _fmt9(p.full_price_copay_total, 10),                 # 266-275 건강보험(의료급여)100/100본인부담금총액
        _fmt9(p.veterans_copay, 10),                         # 276-285 보훈본인일부부담금
        _fmt9(p.under_full_total, 10),                       # 286-295 100분의100미만총액
        _fmt9(p.under_full_copay, 10),                       # 296-305 100분의100미만본인일부부담금
        _fmt9(p.under_full_claim, 10),                       # 306-315 100분의100미만청구액
        _fmt9(p.under_full_veterans_claim, 10),              # 316-325 100분의100미만보훈청구액
    ]
    return _build(parts, 325)


# ---------------------------------------------------------------------------
# 레코드 2-1: 한방 명세서 상병내역 (KCD 진단코드)
# ---------------------------------------------------------------------------

@dataclass
class DiagnosisRecord:
    key: RecordKey
    kcd_code: str                  # 상병분류기호 an(6)
    disease_class: str = "1"       # 상병분류구분 an(1): 1주상병 2부상병 3배제된상병
    treatment_dept: int = 9        # 진료과목 an(2) (별표5, 한의과)
    onset_date: str = "00000000"   # 내원일자/당월요양개시일 an(8) CCYYMMDD
    license_kind: str = "3"        # 면허종류 an(1): 3=한의사
    license_no: str = ""           # 면허번호 an(10)


_KCD_STRIP_CHARS = str.maketrans("", "", ".*†")


def build_diagnosis_record(d: DiagnosisRecord) -> str:
    """레코드 2-1 생성 (43 bytes + CRLF).

    상병분류기호는 특수기호(.,*,†)를 제거하고 6자리 미만이면 뒤 공백 패딩한다.
    """
    kcd = d.kcd_code.translate(_KCD_STRIP_CHARS)
    parts = [
        *_key_parts(d.key),                # 1-15   청구번호+명세서일련번호
        _fmtx(d.disease_class, 1),         # 16     상병분류구분
        _fmtx(kcd, 6),                     # 17-22  상병분류기호
        _fmt9(d.treatment_dept, 2),        # 23-24  진료과목
        _fmt9(int(d.onset_date), 8),       # 25-32  내원일자/당월요양개시일
        _fmtx(d.license_kind, 1),          # 33     면허종류
        _fmtx(d.license_no, 10),           # 34-43  면허번호
    ]
    return _build(parts, 43)


# ---------------------------------------------------------------------------
# 레코드 3: 한방 명세서 진료내역
# ---------------------------------------------------------------------------

@dataclass
class ProcedureDetail:
    key: RecordKey
    hang: str               # 항번호 an(2)
    mok: str                # 목번호 an(2)
    line_no: int            # 줄번호 n(4): 0001부터 순차
    code_gubun: str         # 코드구분 an(1): A수가 B준용수가 C약가 H치료재료
    code: str               # 코드 an(9)
    unit_price: Decimal     # 단가 n(10.2)
    qty: Decimal = Decimal("0")  # 1일투여량·투여(실시)횟수 n(5.2)
    days: int = 0                # 총투여일수·실시횟수 n(3)
    amount: int = 0              # 금액 n(10)
    gamigam_gubun: str = ""      # 가감 등 구분 an(10): 기준처방B### 가미제A### 감미제S### 임의처방H###
    change_date: str = ""        # 변경일 an(8) CCYYMMDD: 당월요양개시일 이후 단가 변경/신설 시 최초 투여(실시)일자. 해당없으면 공란
    license_kind: str = "3"      # 면허종류 an(1): 3=한의사 6=간호사 7=사회복지사 (실제 시행한 사람 기준)
    license_no: str = ""         # 면허번호 an(100): 실제 시행한 사람의 면허번호. 2개 이상이면 "/"로 구분


def build_procedure_record(p: ProcedureDetail) -> str:
    """레코드 3 생성 (184 bytes + CRLF).

    면허종류·면허번호는 변경일(pos76) 뒤에 온다 — 「요양급여비용 청구방법,
    심사청구서·명세서서식 및 작성요령」 p.134~136 "3) 명세서 진료내역"
    원문으로 재확인, 2026-07-11. 0bc5b51에서 제거했던 건 위치/길이(면허번호
    an(10))가 틀렸던 걸 "필드 자체가 없어야 한다"고 오판한 것이었음.
    """
    parts = [
        *_key_parts(p.key),                 # 1-15    청구번호+명세서일련번호
        _fmtx(p.hang, 2),                   # 16-17   항번호
        _fmt9(int(p.mok), 2),               # 18-19   목번호
        _fmt9(p.line_no, 4),                # 20-23   줄번호
        _fmtx(p.code_gubun, 1),             # 24      코드구분
        _fmtx(p.code, 9),                   # 25-33   코드
        _fmt9v9(p.unit_price, 10, 2),       # 34-45   단가
        _fmt9v9(p.qty, 5, 2),               # 46-52   1일투여량·투여(실시)횟수
        _fmt9(p.days, 3),                   # 53-55   총투여일수·실시횟수
        _fmt9(p.amount, 10),                # 56-65   금액
        _fmtx(p.gamigam_gubun, 10),         # 66-75   가감 등 구분
        _fmtx(p.change_date, 8),            # 76-83   변경일
        _fmtx(p.license_kind, 1),           # 84      면허종류
        _fmtx(p.license_no, 100),           # 85-184  면허번호
    ]
    return _build(parts, 184)


# ---------------------------------------------------------------------------
# 레코드 4: 명세서 특정내역기재란 (공통, JS011 경혈코드 등)
# ---------------------------------------------------------------------------

@dataclass
class SpecialRecord:
    key: RecordKey
    record_group_type: str  # 발생단위구분 an(1): 1명세서단위 2줄번호단위 3처방내역줄번호단위 4처방내역단위
    line_no: int             # 줄번호 n(4)
    special_code: str        # 특정내역구분 an(5): 별표8 (예: JS011 경혈코드)
    content: str              # 특정내역 an(700)


def build_special_record(s: SpecialRecord) -> str:
    """레코드 4 생성 (725 bytes + CRLF).

    한방은 「요양급여비용 청구방법, 심사청구서·명세서서식 및 작성요령」
    p.137 "4) 명세서 특정내역기재란" 기준 내역구분·처방전발급번호 필드가
    없다 — 2026-07-11 MCPoS 실측(최소/최대 725바이트)으로 확인.
    """
    parts = [
        *_key_parts(s.key),                 # 1-15   청구번호+명세서일련번호
        _fmtx(s.record_group_type, 1),      # 16     발생단위구분
        _fmt9(s.line_no, 4),                # 17-20  줄번호
        _fmtx(s.special_code, 5),           # 21-25  특정내역구분
        _fmtx(s.content, 700),              # 26-725 특정내역
    ]
    return _build(parts, 725)


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
            if serial == patient.key.record_serial:
                lines.append(build_diagnosis_record(diag))

        for serial, proc in edi.procedure_records:
            if serial == patient.key.record_serial:
                lines.append(build_procedure_record(proc))

        for serial, special in edi.special_records:
            if serial == patient.key.record_serial:
                lines.append(build_special_record(special))

    return "".join(lines).encode("euc-kr", errors="replace")


def generate_sam_files(edi: EDIFile) -> dict[str, bytes]:
    """SAM File 생성 디렉토리(/HIRA/DDMD/SAM/IN/)에 들어갈 개별 파일들을
    레코드 종류별로 나눠 생성한다 (한방은 청구서+명세서가 한 파일로
    합쳐지는 의·치과와 달리 H010 + K020.1~4로 분리해야 함).

    H010: 요양급여비용(의료급여비용)심사청구서 (헤더, 공통)
    K020.1: 일반내역 (환자/청구 기본정보)
    K020.2: 상병내역 (진단)
    K020.3: 진료내역 (시술·처치)
    K020.4: 특정내역
    H060: 치료재료 및 약제 구입내역통보서 — 현재는 dummy(0KB) 고정, 추후
          실제 구매내역 입력 기능 추가 시 교체 필요 (아래 주석 참고)

    해당 레코드가 없는 파일도 0바이트 더미 파일로 포함한다 (SAM File
    작성 규칙 — 발생하지 않는 SAM File이라도 Dummy file을 생성해야 함).
    """
    def _join(lines: list[str]) -> bytes:
        return "".join(lines).encode("euc-kr", errors="replace")

    return {
        "H010": _join([build_claim_header(edi.header)]),
        "K020.1": _join([build_patient_record(p) for p in edi.patient_records]),
        "K020.2": _join([build_diagnosis_record(d) for _, d in edi.diagnosis_records]),
        "K020.3": _join([build_procedure_record(p) for _, p in edi.procedure_records]),
        "K020.4": _join([build_special_record(s) for _, s in edi.special_records]),
        # H060(치료재료 및 약제 구입내역통보서): 이 앱은 치료재료·원료약 구매내역을
        # 입력받는 기능이 없고 한방에서는 대부분 발생하지 않는 항목이라, 「전자문서작성요령」
        # 규칙("발생하지 않는 SAM File이라도 Dummy file을 생성해야 한다")에 따라 항상
        # 0바이트로 생성한다. 구매내역 입력 기능이 생기면 이 자리를 실제 데이터로 교체.
        "H060": b"",
    }
