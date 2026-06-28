"""KMISHE EDIFACT 전자문서 생성기.

HIRA 건강보험 요양급여비용 전자문서 (별표1) 기준.
한방용 요양급여(의료급여)비용 명세서 (KMISHE) — UN/EDIFACT D:96A.

전자문서 구조 (06한방명세서2.pdf 기준):
  HEADER : UNH, BGM, NAD×3, RFF×5
  BODY   : UNS, Gr.1(접수), NAD×3, RFF×3, Gr.2, FTX,
           Gr.3(상병/특성 ×40), Gr.4(일수 ×15), RFF, TDT,
           Gr.5(환불), Gr.6(자동화), Gr.7(진료내역 ×9999)
  SUMMARY: UNS, Gr.8(금액 ×20), FTX, Gr.9, Gr.10, Gr.11(특정내역), Gr.12(AUT), UNT

NOTE: CCI/AGR HIRA 특성항목 코드는 공식 배포 코드표 확인 필요.
      BGM 문서유형코드 GI012 = 한방 명세서 제출, GI013 = 응답.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


# ── EDIFACT 구분자 (UNA 기준) ──────────────────────────────────────────────────
_CE  = ":"   # 복합 요소 구분자
_DE  = "+"   # 데이터 요소 구분자
_SEG = "'"   # 세그먼트 종결자
_ESC = "?"   # 릴리즈 문자

UNA = f"UNA{_CE}{_DE}.{_ESC} {_SEG}"


def _esc(v: str) -> str:
    """EDIFACT 특수문자 이스케이프."""
    for ch in (_ESC, _DE, _CE, _SEG):
        v = v.replace(ch, _ESC + ch)
    return v


def _s(tag: str, *parts: str) -> str:
    """세그먼트 한 줄 생성: TAG+p1+p2+...' """
    elements = [tag, *parts]
    while len(elements) > 1 and elements[-1] == "":
        elements.pop()
    return _DE.join(elements) + _SEG


def _c(*components: str) -> str:
    """복합 데이터 요소: c1:c2:c3"""
    items = list(components)
    while items and items[-1] == "":
        items.pop()
    return _CE.join(items)


# ── 데이터 클래스 ──────────────────────────────────────────────────────────────

@dataclass
class KmisheInstitution:
    code: str        # 요양기관기호 8자리
    name: str        # 요양기관명
    type_code: str   # 종별구분 (한의원=13)
    claim_type: str  # 보험자종별 (건강보험=4, 의료급여=5, 보훈=7)


@dataclass
class KmisheDiagnosis:
    kcd_code: str           # 상병분류기호 (예: U22.0)
    onset_date: str         # 당월요양개시일 CCYYMMDD
    treatment_dept: str     # 진료과목 코드 (한방과=39)
    result_code: str = "T"  # 진료결과 (T=완치, O=호전, C=계속, D=사망)
    license_type: str = "3" # 면허종류 (3=한의사)
    license_no: str = ""    # 면허번호


@dataclass
class KmisheProcedure:
    line_no: int           # 줄번호
    code: str              # 행위코드 X(8)
    code_type: str         # 코드구분 (A=수가, B=전용, C=약가, H=치료재료)
    unit_price: Decimal    # 단가
    qty: Decimal           # 1회투여량/실시횟수
    days: int              # 총투여일수/실시횟수
    amount: int            # 금액
    license_type: str = "3"
    license_no: str = ""
    change_date: str = ""
    adjustment_type: str = ""


@dataclass
class KmisheAmounts:
    benefit_total_1: int = 0      # 요양급여비용총액1
    copayment: int = 0            # 본인일부부담금
    claim_amount: int = 0         # 청구액
    support_fund: int = 0         # 지원금
    upper_limit_excess: int = 0   # 본인부담상한액초과금
    deferred_payment: int = 0     # 대불금
    disability_medical: int = 0   # 장애인의료비
    benefit_total_2: int = 0      # 요양급여비용총액2/진료비총액
    veterans_claim: int = 0       # 보훈청구액
    full_price_total: int = 0     # 100/100 본인부담금총액
    veterans_copay: int = 0       # 보훈 본인일부부담금
    under_full_total: int = 0     # 100미만 총액
    under_full_copay: int = 0     # 100미만 본인일부부담금
    under_full_claim: int = 0     # 100미만 청구액
    under_full_veterans: int = 0  # 100미만 보훈청구액


@dataclass
class KmisheSpecialItem:
    special_code: str   # 특정내역구분코드 (예: JX999)
    content: str        # 특정내역 내용
    line_no: str = ""   # 관련 줄번호


@dataclass
class KmisheMessage:
    """KMISHE 메시지 (환자 1명 = 1 메시지)."""
    ref_no: str                  # 메시지 참조번호 (일련번호)
    claim_no: str                # 청구번호 (명세서번호+일련번호)
    treatment_ym: str            # 진료년월 CCYYMM
    institution: KmisheInstitution
    # 수진자
    patient_name: str
    patient_rrn: str             # 주민등록번호 (하이픈 포함 가능)
    subscriber_id: str           # 가입자기호
    cert_no: str = ""
    receipt_no: str = ""
    first_admission_date: str = ""
    # 진료 내용
    diagnoses: list[KmisheDiagnosis] = field(default_factory=list)
    procedures: list[KmisheProcedure] = field(default_factory=list)
    amounts: KmisheAmounts = field(default_factory=KmisheAmounts)
    special_items: list[KmisheSpecialItem] = field(default_factory=list)
    benefit_days: int = 0
    total_visits: int = 0
    inpatient_days: int = 0


# ── 세그먼트 빌더 ──────────────────────────────────────────────────────────────

def _unh(ref_no: str) -> str:
    return _s("UNH", ref_no, _c("KMISHE", "D", "96A", "UN"))


def _bgm(claim_no: str) -> str:
    # GI012 = 한방 명세서 제출 (HIRA 문서유형코드)
    return _s("BGM", _c("GI012"), _esc(claim_no), "9")


def _nad_institution(inst: KmisheInstitution) -> list[str]:
    return [
        _s("NAD", "MS", _c(inst.code, "", "", _esc(inst.name))),  # 요양기관 (발신)
        _s("NAD", "ZZZ", _c(inst.type_code)),                      # 종별구분
        _s("NAD", "MR", _c("HIRA", "", "", "심평원")),              # 심평원 (수신)
    ]


def _rff_header(claim_no: str, inst_code: str, claim_type: str) -> list[str]:
    return [
        _s("RFF", _c("ABO", _esc(claim_no))),    # 청구번호
        _s("RFF", _c("MA", inst_code)),           # 요양기관기호
        _s("RFF", _c("ZZZ", claim_type)),         # 보험자종별구분
    ]


def _gr1_receipt(receipt_no: str, first_admission_date: str) -> list[str]:
    segs = []
    if receipt_no:
        segs.append(_s("RFF", _c("ACK", receipt_no)))
    if first_admission_date and first_admission_date != "00000000":
        segs.append(_s("DTM", _c("182", first_admission_date, "102")))
    return segs


def _nad_patient(name: str, subscriber_id: str) -> list[str]:
    return [
        _s("NAD", "BI", _c(subscriber_id, "", "", _esc(name))),
        _s("NAD", "PO", _c("", "", "", _esc(name))),  # 수진자성명
        _s("NAD", "ZZZ", ""),                          # 노숙인시설기호 (해당없음)
    ]


def _rff_patient(rrn: str, cert_no: str, subscriber_id: str) -> list[str]:
    rrn_clean = rrn.replace("-", "")
    segs = [_s("RFF", _c("PQ", rrn_clean))]  # 주민등록번호
    if cert_no:
        segs.append(_s("RFF", _c("ACD", _esc(cert_no))))
    if subscriber_id:
        segs.append(_s("RFF", _c("MA", _esc(subscriber_id))))
    return segs


def _gr3_diagnoses(diagnoses: list[KmisheDiagnosis]) -> list[str]:
    """Gr.3: 상병/진료특성 (CCI ×40)."""
    segs = []
    for diag in diagnoses:
        # 상병분류기호
        segs.append(_s("CCI", "A", "", _c("ZZZ", _esc(diag.kcd_code))))
        if diag.onset_date:
            segs.append(_s("DTM", _c("182", diag.onset_date, "102")))
        if diag.result_code:
            segs.append(_s("ATT", "A", "", _c("ZZZ", diag.result_code)))
    # 진료과목 (첫 번째 상병 기준)
    if diagnoses:
        segs.append(_s("CCI", "B", "", _c("ZZZ", diagnoses[0].treatment_dept)))
        if diagnoses[0].license_no:
            segs.append(_s("TDT", "1", "", _c(diagnoses[0].license_type, diagnoses[0].license_no)))
    return segs


def _gr4_days(benefit_days: int, total_visits: int, inpatient_days: int) -> list[str]:
    """Gr.4: 요양급여일수/내원일수."""
    segs = []
    if benefit_days:
        segs.append(_s("QTY", _c("59", str(benefit_days))))
    if total_visits:
        segs.append(_s("QTY", _c("38", str(total_visits))))
    if inpatient_days:
        segs.append(_s("QTY", _c("164", str(inpatient_days))))
    return segs


def _gr7_procedures(procedures: list[KmisheProcedure]) -> list[str]:
    """Gr.7: 진료내역 줄단위 (LIN ×9999)."""
    segs = []
    for proc in procedures:
        segs.append(_s("LIN", str(proc.line_no)))
        segs.append(_s("FTX", "ACB", "", _c(proc.code_type, _esc(proc.code))))
        segs.append(_s("QTY", _c("59", str(proc.qty))))
        segs.append(_s("QTY", _c("38", str(proc.days))))
        segs.append(_s("PRI", _c("AAA", str(proc.unit_price), "CAL")))
        segs.append(_s("FTX", "AAA", "", str(proc.amount)))
        if proc.license_no:
            segs.append(_s("TDT", "1", "", _c(proc.license_type, proc.license_no)))
        if proc.adjustment_type:
            segs.append(_s("FTX", "ZZZ", "", _esc(proc.adjustment_type)))
    return segs


# MOA qualifier 매핑 (EDIFACT 표준 + HIRA 정의)
_MOA_QUALIFIERS = [
    ("77",  "benefit_total_1"),    # 요양급여비용총액1
    ("125", "copayment"),          # 본인일부부담금
    ("128", "claim_amount"),       # 청구액
    ("204", "support_fund"),       # 지원금
    ("8",   "upper_limit_excess"), # 본인부담상한액초과금
    ("23",  "deferred_payment"),   # 대불금
    ("ZZZ", "disability_medical"), # 장애인의료비 (HIRA 정의)
    ("ZZZ", "benefit_total_2"),    # 요양급여비용총액2 (HIRA 정의)
    ("ZZZ", "veterans_claim"),     # 보훈청구액 (HIRA 정의)
    ("ZZZ", "full_price_total"),   # 100/100 본인부담금총액 (HIRA 정의)
    ("ZZZ", "veterans_copay"),     # 보훈 본인일부부담금 (HIRA 정의)
    ("ZZZ", "under_full_total"),   # 100미만 총액 (HIRA 정의)
    ("ZZZ", "under_full_copay"),   # 100미만 본인일부부담금 (HIRA 정의)
    ("ZZZ", "under_full_claim"),   # 100미만 청구액 (HIRA 정의)
    ("ZZZ", "under_full_veterans"),# 100미만 보훈청구액 (HIRA 정의)
]


def _gr8_amounts(amounts: KmisheAmounts) -> list[str]:
    """Gr.8: 금액 합계 (MOA ×20)."""
    segs = []
    for qualifier, attr in _MOA_QUALIFIERS:
        value = getattr(amounts, attr, 0)
        if value:
            segs.append(_s("MOA", _c(qualifier, str(value))))
    return segs


def _gr11_special(special_items: list[KmisheSpecialItem]) -> list[str]:
    """Gr.11: 특정내역 (AGR+FTX ×999)."""
    segs = []
    for item in special_items:
        segs.append(_s("AGR", _c("ZZZ", _esc(item.special_code))))
        segs.append(_s("FTX", "ACB", "", _esc(item.content)))
        if item.line_no:
            segs.append(_s("ATT", "A", "", _c("ZZZ", item.line_no)))
    return segs


def _unt(segment_count: int, ref_no: str) -> str:
    return _s("UNT", str(segment_count), ref_no)


# ── 메시지 조립 ───────────────────────────────────────────────────────────────

def build_kmishe_message(msg: KmisheMessage) -> str:
    """KMISHE 메시지 전체 생성 (UNH~UNT)."""
    segs: list[str] = []

    # HEADER
    segs.append(_unh(msg.ref_no))
    segs.append(_bgm(msg.claim_no))
    segs.extend(_nad_institution(msg.institution))
    segs.extend(_rff_header(msg.claim_no, msg.institution.code, msg.institution.claim_type))

    # BODY
    segs.append(_s("UNS", "D"))
    segs.extend(_gr1_receipt(msg.receipt_no, msg.first_admission_date))
    segs.extend(_nad_patient(msg.patient_name, msg.subscriber_id))
    segs.extend(_rff_patient(msg.patient_rrn, msg.cert_no, msg.subscriber_id))
    segs.extend(_gr3_diagnoses(msg.diagnoses))
    segs.extend(_gr4_days(msg.benefit_days, msg.total_visits, msg.inpatient_days))
    segs.extend(_gr7_procedures(msg.procedures))

    # SUMMARY
    segs.append(_s("UNS", "S"))
    segs.extend(_gr8_amounts(msg.amounts))
    if msg.special_items:
        segs.extend(_gr11_special(msg.special_items))

    # UNT: UNH+UNT 포함한 세그먼트 총 수
    segs.append(_unt(len(segs) + 1, msg.ref_no))

    return "".join(segs)


# ── 인터체인지 래퍼 (UNB/UNZ) ─────────────────────────────────────────────────

def build_interchange(
    messages: list[str],
    sender_id: str,
    receiver_id: str = "HIRA",
    control_ref: str = "1",
    ts: datetime | None = None,
) -> bytes:
    """EDIFACT 인터체인지 전체 (UNA + UNB + messages + UNZ), EUC-KR 인코딩."""
    if ts is None:
        ts = datetime.now()

    unb = _s("UNB",
        _c("UNOA", "1"),
        _c(_esc(sender_id), "1"),
        _c(_esc(receiver_id), "1"),
        _c(ts.strftime("%y%m%d"), ts.strftime("%H%M")),
        control_ref,
    )
    unz = _s("UNZ", str(len(messages)), control_ref)

    full = UNA + "\n" + unb + "".join(messages) + unz
    return full.encode("euc-kr", errors="replace")
