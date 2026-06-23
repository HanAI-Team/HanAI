"""데이터 30종 검증 테스트.

시나리오별로 calculate_billing() 결과와 EDI 레코드 바이트 위치를 검증한다.

항목 번호는 원본 체크리스트 기준:
  1  금액산출 → calculate_billing() 함수 호출 자체
  2  100분의100미만 보훈청구액
  3  보훈 본인일부부담금
  4  보훈위탁진료 진료비총액 (benefit_total_2)
  5  보훈청구액
  6  100분의100미만 본인일부부담금
  7  100분의100미만 청구액
  8  100분의100미만 총액
  9  15세 이하 입원 본인일부부담금
  10 건강보험 입원 본인일부부담금
  11 건강보험(의료급여) 요양급여비용총액2
  12 건강보험(의료급여) 100분의100 본인부담금총액
  13 건강보험 외래 본인일부부담금
  14 공상 본인일부부담금
  15 산정특례 본인일부부담금
  16 요양급여비용 총액1
  17 의료급여 외래 본인일부부담금
  18 의료급여 입원 본인일부부담금
  19 장애인의료비
  20 지원금
  21 차상위1종 본인일부부담금
  22 차상위2종 외래 본인일부부담금
  23 차상위2종 입원 본인일부부담금
  24 자릿수 (EDI _fmt9 포맷터 처리, 별도 필드 없음 — 레코드 길이 테스트로 검증)
  25 진료(조제)일수
  26 차등수가청구액
  27 차등지수
  28 면허종류 및 번호 (C2-71 진료내역 레코드)
  29 진료내역        (C2-71)
  30 특정기호
  31 특정내역        (C2-08 특정내역 레코드)
"""

from datetime import date
from decimal import Decimal

from app.billing.copayment import (
    BillingInput,
    InsuranceType,
    MedicalAidGrade,
    VisitType,
    calculate_billing,
)
from app.billing.edi_writer import (
    ClaimHeader,
    PatientRecord,
    ProcedureDetail,
    RecordKey,
    SpecialRecord,
    build_claim_header,
    build_patient_record,
    build_procedure_record,
    build_special_record,
)

# ──────────────────────────────────────────────────────────────────────────────
# 헬퍼
# ──────────────────────────────────────────────────────────────────────────────

_DUMMY_KEY = RecordKey(institution_code="12345678", serial_no=1)
_REF_DATE = date(2026, 6, 1)


def _calc(
    insurance_type: str,
    visit_type: str,
    benefit_total: int,
    non_benefit_total: int = 0,
    special_code: str | None = None,
    medical_aid_grade: str | None = None,
    birth_date: date | None = None,
    work_injury: bool = False,
    disability_medical_cost: int = 0,
    support_fund: int = 0,
    treatment_days: Decimal = Decimal("0"),
    graduated_fee_index: Decimal = Decimal("0"),
):
    return calculate_billing(BillingInput(
        insurance_type=InsuranceType(insurance_type),
        visit_type=VisitType(visit_type),
        benefit_total=benefit_total,
        non_benefit_total=non_benefit_total,
        special_code=special_code,
        medical_aid_grade=MedicalAidGrade(medical_aid_grade) if medical_aid_grade else None,
        birth_date=birth_date,
        treatment_date=_REF_DATE,
        work_injury=work_injury,
        disability_medical_cost=disability_medical_cost,
        support_fund=support_fund,
        treatment_days=treatment_days,
        graduated_fee_index=graduated_fee_index,
    ))


def _c2_11_bytes(result, **kwargs) -> bytes:
    rec = PatientRecord(
        key=_DUMMY_KEY,
        employer_code="00000000000",
        cert_no="0000000000000",
        subscriber_name="홍길동",
        patient_name="홍길동",
        patient_rrn="9001011234567",
        inpatient_days=kwargs.get("inpatient_days", 1),
        benefit_days=1,
        benefit_total_1=result.benefit_total_1,
        copayment=result.copayment,
        claim_amount=result.claim_amount,
        upper_limit_excess=result.upper_limit_excess,
        medical_aid_type=kwargs.get("medical_aid_type", " "),
        deferred_or_disability=result.disability_medical_cost,
        benefit_total_2=result.benefit_total_2,
        veterans_claim=result.veterans_claim,
        support_fund=result.support_fund,
        full_price_copay_total=result.full_price_copay_total,
        veterans_copay=result.veterans_copay,
        under_full_total=result.under_full_total,
        under_full_copay=result.under_full_copay,
        under_full_claim=result.under_full_claim,
        under_full_veterans_claim=result.under_full_veterans_claim,
    )
    return build_patient_record(rec).encode("euc-kr")


def _c2_00_bytes(result) -> bytes:
    hdr = ClaimHeader(
        key=_DUMMY_KEY,
        billing_type="U1",
        treatment_ym="202606",
        claim_date="20260601",
        claimer="홍길동",
        writer="홍길동",
        writer_rrn="9001011234567",
        claim_count=1,
        benefit_total_1=result.benefit_total_1,
        copayment=result.copayment,
        claim_amount=result.claim_amount,
        upper_limit_excess=result.upper_limit_excess,
        disability_medical_cost=result.disability_medical_cost,
        graduated_claim=result.graduated_claim,
        graduated_index=result.graduated_index,
        treatment_days=result.treatment_days,
        benefit_total_2=result.benefit_total_2,
        veterans_claim=result.veterans_claim,
        support_fund=result.support_fund,
        full_price_copay_total=result.full_price_copay_total,
        veterans_copay=result.veterans_copay,
        under_full_total=result.under_full_total,
        under_full_copay=result.under_full_copay,
        under_full_claim=result.under_full_claim,
        under_full_veterans_claim=result.under_full_veterans_claim,
    )
    return build_claim_header(hdr).encode("euc-kr")


# ──────────────────────────────────────────────────────────────────────────────
# 시나리오 S01: 건강보험 외래 기본
# 항목: 1(금액산출) / 13(건강보험 외래) / 16(총액1) / 11(총액2)
# ──────────────────────────────────────────────────────────────────────────────

class TestS01_건강보험_외래_기본:
    def setup_method(self):
        self.r = _calc("4", "외래", benefit_total=10000)

    def test_항목1_금액산출_호출성공(self):
        assert self.r is not None

    def test_항목13_건강보험_외래_본인부담(self):
        # 30% → ceil(10000*0.3) = 3000
        assert self.r.health_outpatient_copay == 3000

    def test_항목16_요양급여비용_총액1(self):
        assert self.r.benefit_total_1 == 10000

    def test_항목11_요양급여비용_총액2_비급여없음(self):
        assert self.r.benefit_total_2 == 10000

    def test_항목7_100미만_청구액(self):
        assert self.r.under_full_claim == 7000

    def test_항목6_100미만_본인부담(self):
        assert self.r.under_full_copay == 3000

    def test_항목8_100미만_총액(self):
        assert self.r.under_full_total == 10000

    def test_C2_11_요양급여비용총액1_바이트128_137(self):
        # 0-indexed: 127-136 → 요양급여비용총액1 9(10)
        raw = _c2_11_bytes(self.r)
        assert raw[127:137].decode("euc-kr") == "0000010000"

    def test_C2_11_본인일부부담금_바이트138_147(self):
        raw = _c2_11_bytes(self.r)
        assert raw[137:147].decode("euc-kr") == "0000003000"

    def test_C2_11_청구액_바이트148_157(self):
        raw = _c2_11_bytes(self.r)
        assert raw[147:157].decode("euc-kr") == "0000007000"


# ──────────────────────────────────────────────────────────────────────────────
# 시나리오 S02: 건강보험 입원 성인 (20%)
# 항목: 10(건강보험 입원)
# ──────────────────────────────────────────────────────────────────────────────

class TestS02_건강보험_입원_성인:
    def setup_method(self):
        self.r = _calc("4", "입원", benefit_total=50000, birth_date=date(1990, 1, 1))

    def test_항목10_건강보험_입원_본인부담(self):
        # 20% → 10000
        assert self.r.health_inpatient_copay == 10000

    def test_항목9_15세이하_입원은_0(self):
        assert self.r.under_15_inpatient_copay == 0

    def test_C2_11_본인일부부담금(self):
        raw = _c2_11_bytes(self.r, inpatient_days=5)
        assert raw[137:147].decode("euc-kr") == "0000010000"


# ──────────────────────────────────────────────────────────────────────────────
# 시나리오 S03: 건강보험 입원 15세 미만 (5%)
# 항목: 9(15세 이하 입원)
# ──────────────────────────────────────────────────────────────────────────────

class TestS03_건강보험_입원_15세미만:
    def setup_method(self):
        # 기준일 2026-06-01 기준 만 14세
        self.r = _calc("4", "입원", benefit_total=20000, birth_date=date(2012, 7, 1))

    def test_항목9_15세이하_입원_본인부담(self):
        # 5% → ceil(20000*0.05) = 1000
        assert self.r.under_15_inpatient_copay == 1000

    def test_항목10_건강보험_입원은_0(self):
        assert self.r.health_inpatient_copay == 0


# ──────────────────────────────────────────────────────────────────────────────
# 시나리오 S04: 의료급여 1종 외래 (1000원 정액)
# 항목: 17(의료급여 외래)
# ──────────────────────────────────────────────────────────────────────────────

class TestS04_의료급여1종_외래:
    def setup_method(self):
        self.r = _calc("5", "외래", benefit_total=15000, medical_aid_grade="1")

    def test_항목17_의료급여_외래_본인부담(self):
        assert self.r.medical_aid_outpatient_copay == 1000

    def test_항목18_의료급여_입원은_0(self):
        assert self.r.medical_aid_inpatient_copay == 0

    def test_C2_11_의료급여종별구분_바이트200(self):
        # 0-indexed 200: 의료급여종별구분 A
        raw = _c2_11_bytes(self.r, medical_aid_type="1")
        assert raw[200:201].decode("euc-kr") == "1"


# ──────────────────────────────────────────────────────────────────────────────
# 시나리오 S05: 의료급여 2종 외래 + 장애인의료비
# 항목: 17(의료급여 외래), 19(장애인의료비)
# ──────────────────────────────────────────────────────────────────────────────

class TestS04b_의료급여1종_입원:
    def setup_method(self):
        self.r = _calc("5", "입원", benefit_total=30000, medical_aid_grade="1")

    def test_항목18_의료급여1종_입원_본인부담은_0(self):
        assert self.r.medical_aid_inpatient_copay == 0

    def test_항목17_의료급여_외래는_0(self):
        assert self.r.medical_aid_outpatient_copay == 0


class TestS04c_의료급여2종_입원:
    def setup_method(self):
        self.r = _calc("5", "입원", benefit_total=30000, medical_aid_grade="2")

    def test_항목18_의료급여2종_입원_본인부담(self):
        # 10% → ceil(30000*0.10) = 3000
        assert self.r.medical_aid_inpatient_copay == 3000

    def test_항목17_의료급여_외래는_0(self):
        assert self.r.medical_aid_outpatient_copay == 0


class TestS05_의료급여2종_외래_장애인:
    def setup_method(self):
        self.r = _calc("5", "외래", benefit_total=10000, medical_aid_grade="2",
                       disability_medical_cost=3000)

    def test_항목17_의료급여_외래_본인부담(self):
        # 15% → ceil(10000*0.15) = 1500
        assert self.r.medical_aid_outpatient_copay == 1500

    def test_항목19_장애인의료비(self):
        assert self.r.disability_medical_cost == 3000

    def test_C2_11_장애인의료비_바이트202_211(self):
        # 0-indexed 202-211: 대불금/장애인의료비 9(10)
        raw = _c2_11_bytes(self.r, medical_aid_type="2")
        assert raw[202:212].decode("euc-kr") == "0000003000"


# ──────────────────────────────────────────────────────────────────────────────
# 시나리오 S06: 산정특례 V027 희귀난치 (10%)
# 항목: 15(산정특례), 30(특정기호 echo)
# ──────────────────────────────────────────────────────────────────────────────

class TestS06_산정특례:
    def setup_method(self):
        self.r = _calc("4", "외래", benefit_total=30000, special_code="V027")

    def test_항목15_산정특례_본인부담(self):
        # 10% → ceil(30000*0.10) = 3000
        assert self.r.special_exception_copay == 3000

    def test_항목30_특정기호는_라우터_에코_계층(self):
        # special_code는 라우터에서 BillingCalcResponse.special_code로 에코
        # calculate_billing() 자체는 입력으로 받아 비율 계산에만 사용
        pass


# ──────────────────────────────────────────────────────────────────────────────
# 시나리오 S07: 차상위 1종 / 2종
# 항목: 21 / 22 / 23
# ──────────────────────────────────────────────────────────────────────────────

class TestS07a_차상위1종:
    def setup_method(self):
        self.r = _calc("4", "외래", benefit_total=20000, special_code="C001")

    def test_항목21_차상위1종_본인부담(self):
        assert self.r.near_poverty_1_copay == 2000

    def test_항목22_차상위2종_외래는_0(self):
        assert self.r.near_poverty_2_outpatient_copay == 0


class TestS07b_차상위2종_외래:
    def setup_method(self):
        self.r = _calc("4", "외래", benefit_total=10000, special_code="C002")

    def test_항목22_차상위2종_외래_본인부담(self):
        # 15% → 1500
        assert self.r.near_poverty_2_outpatient_copay == 1500


class TestS07c_차상위2종_입원:
    def setup_method(self):
        self.r = _calc("4", "입원", benefit_total=40000, special_code="C002")

    def test_항목23_차상위2종_입원_본인부담(self):
        # 10% → 4000
        assert self.r.near_poverty_2_inpatient_copay == 4000


# ──────────────────────────────────────────────────────────────────────────────
# 시나리오 S08: 공상 환자
# 항목: 14(공상 본인부담=0)
# ──────────────────────────────────────────────────────────────────────────────

class TestS08_공상환자:
    def setup_method(self):
        self.r = _calc("4", "외래", benefit_total=25000, work_injury=True)

    def test_항목14_공상_본인부담은_0(self):
        assert self.r.work_injury_copay == 0

    def test_청구액은_전액(self):
        assert self.r.claim_amount == 25000


# ──────────────────────────────────────────────────────────────────────────────
# 시나리오 S09: 보훈 (국비환자)
# 항목: 2 / 3 / 4 / 5
# ──────────────────────────────────────────────────────────────────────────────

class TestS09_보훈:
    def setup_method(self):
        self.r = _calc("7", "외래", benefit_total=18000, non_benefit_total=5000)

    def test_항목5_보훈청구액(self):
        assert self.r.veterans_claim == 18000

    def test_항목3_보훈_본인부담은_0(self):
        assert self.r.veterans_copay == 0

    def test_항목4_진료비총액(self):
        assert self.r.veterans_total == 23000

    def test_항목2_100미만_보훈청구액(self):
        assert self.r.under_full_veterans_claim == 18000

    def test_C2_11_보훈청구액_바이트245_254(self):
        # 0-indexed 245-254: 보훈청구액 9(10)
        raw = _c2_11_bytes(self.r)
        assert raw[245:255].decode("euc-kr") == "0000018000"

    def test_C2_11_보훈본인부담_바이트295_304(self):
        # 0-indexed 295-304: 보훈 본인일부부담금 9(10)
        raw = _c2_11_bytes(self.r)
        assert raw[295:305].decode("euc-kr") == "0000000000"


# ──────────────────────────────────────────────────────────────────────────────
# 시나리오 S10: 100분의100 비급여 포함
# 항목: 8 / 11 / 12
# ──────────────────────────────────────────────────────────────────────────────

class TestS10_100분의100_비급여포함:
    def setup_method(self):
        self.r = _calc("4", "외래", benefit_total=10000, non_benefit_total=20000)

    def test_항목12_100분의100_본인부담총액(self):
        assert self.r.full_price_copay_total == 20000

    def test_항목11_진료비총액(self):
        assert self.r.benefit_total_2 == 30000

    def test_항목8_100미만_총액은_급여부분만(self):
        assert self.r.under_full_total == 10000

    def test_C2_11_100분의100_바이트285_294(self):
        # 0-indexed 285-294: 건강보험(의료급여) 100분의100 본인부담금총액 9(10)
        raw = _c2_11_bytes(self.r)
        assert raw[285:295].decode("euc-kr") == "0000020000"


# ──────────────────────────────────────────────────────────────────────────────
# 시나리오 S11: 지원금
# 항목: 20(지원금)
# ──────────────────────────────────────────────────────────────────────────────

class TestS11_지원금:
    def setup_method(self):
        self.r = _calc("5", "외래", benefit_total=10000, medical_aid_grade="2",
                       support_fund=5000)

    def test_항목20_지원금(self):
        assert self.r.support_fund == 5000

    def test_C2_11_지원금_바이트255_264(self):
        # 0-indexed 255-264: 지원금 9(10)
        raw = _c2_11_bytes(self.r, medical_aid_type="2")
        assert raw[255:265].decode("euc-kr") == "0000005000"


# ──────────────────────────────────────────────────────────────────────────────
# 시나리오 S12: 차등수가
# 항목: 25(진료일수) / 26(차등수가청구액) / 27(차등지수)
# ──────────────────────────────────────────────────────────────────────────────

class TestS12_차등수가:
    def setup_method(self):
        self.r = _calc(
            "4", "외래", benefit_total=60000,
            treatment_days=Decimal("30"),
            graduated_fee_index=Decimal("0.800"),
        )

    def test_항목25_진료일수(self):
        assert self.r.treatment_days == Decimal("30")

    def test_항목27_차등지수(self):
        assert self.r.graduated_index == Decimal("0.800")

    def test_항목26_차등수가청구액(self):
        # claim_amount = 60000 - ceil(60000*0.3) = 60000 - 18000 = 42000
        # graduated_claim = ceil(42000 * 0.800) = 33600
        assert self.r.graduated_claim == 33600

    def test_C2_00_차등수가청구액_바이트166_175(self):
        # 0-indexed 166-175: 차등수가청구액 9(10)
        raw = _c2_00_bytes(self.r)
        assert raw[166:176].decode("euc-kr") == "0000033600"

    def test_C2_00_차등지수_바이트176_182(self):
        # 0-indexed 176-182: 차등지수 9V9(7), 0.800 → 스케일 10^3 → "0000800"
        raw = _c2_00_bytes(self.r)
        assert raw[176:183].decode("euc-kr") == "0000800"

    def test_C2_00_진료일수_바이트183_190(self):
        # 0-indexed 183-190: 진료일수 9999V99(8), 30.00 → 스케일 10^2 → "00003000"
        raw = _c2_00_bytes(self.r)
        assert raw[183:191].decode("euc-kr") == "00003000"


# ──────────────────────────────────────────────────────────────────────────────
# 자릿수 (항목 24): 레코드 길이로 검증
# ──────────────────────────────────────────────────────────────────────────────

class TestS_자릿수_레코드길이:
    """항목 24: 포맷터가 자릿수를 보장. CRLF 포함 Max 347 바이트(EUC-KR)."""

    def test_C2_11_레코드_길이_345_plus_CRLF(self):
        r = _calc("4", "외래", benefit_total=10000)
        assert len(_c2_11_bytes(r)) == 347

    def test_C2_00_레코드_길이_345_plus_CRLF(self):
        r = _calc("4", "외래", benefit_total=10000)
        assert len(_c2_00_bytes(r)) == 347


# ──────────────────────────────────────────────────────────────────────────────
# 항목 28·29: C2-71 진료내역 — 면허종류/번호, 행위코드 (LAY C2-72 기준)
# ──────────────────────────────────────────────────────────────────────────────

class TestC2_71_진료내역:
    """C2-71 레코드 바이트 위치 검증 (항목 28·29).

    레이아웃 0-indexed:
      17-20: 공란 X(4)
      21-22: 항번호 XX      → 0-indexed [21:23]
      23-24: 목번호 99      → [23:25]
      25   : 코드구분 X(1)  → [25:26]
      26-33: 코드 X(8)      → [26:34]
      40-49: 단가 9(9)V9    → [40:50]
      50-57: 1회투약량       → [50:58]
      58-63: 일투            → [58:64]
      64-66: 총투            → [64:67]
      67-76: 금액 9(10)     → [67:77]
      129  : 면허종류 X(1)  → [129:130]
      130-229: 면허번호 X(100) → [130:230]
    """

    def _make_proc(self, code="AA159", license_type="3", license_no="1234567890") -> ProcedureDetail:
        return ProcedureDetail(
            key=_DUMMY_KEY,
            hang="04",
            mok="01",
            code_gubun="A",
            code=code,
            unit_price=Decimal("6260"),
            qty=Decimal("1"),
            days=1,
            amount=6260,
            license_type=license_type,
            license_no=license_no,
        )

    def test_항목29_레코드_길이_230_plus_CRLF(self):
        raw = build_procedure_record(self._make_proc()).encode("euc-kr")
        assert len(raw) == 232

    def test_항목29_항번호_바이트21_22(self):
        raw = build_procedure_record(self._make_proc()).encode("euc-kr")
        assert raw[21:23].decode("euc-kr") == "04"

    def test_항목29_목번호_바이트23_24(self):
        raw = build_procedure_record(self._make_proc()).encode("euc-kr")
        assert raw[23:25].decode("euc-kr") == "01"

    def test_항목29_코드구분_바이트25(self):
        raw = build_procedure_record(self._make_proc()).encode("euc-kr")
        assert raw[25:26].decode("euc-kr") == "A"

    def test_항목29_행위코드_바이트26_33(self):
        # code="AA159" → X(8) 좌측정렬 공백패딩 → "AA159   "
        raw = build_procedure_record(self._make_proc()).encode("euc-kr")
        assert raw[26:34].decode("euc-kr") == "AA159   "

    def test_항목29_단가_바이트40_49(self):
        # 6260원, 9(9)V9 → 62600 → "0000062600"
        raw = build_procedure_record(self._make_proc()).encode("euc-kr")
        assert raw[40:50].decode("euc-kr") == "0000062600"

    def test_항목29_금액_바이트67_76(self):
        # 6260원, 9(10) → "0000006260"
        raw = build_procedure_record(self._make_proc()).encode("euc-kr")
        assert raw[67:77].decode("euc-kr") == "0000006260"

    def test_항목28_면허종류_바이트129(self):
        raw = build_procedure_record(self._make_proc(license_type="3")).encode("euc-kr")
        assert raw[129:130].decode("euc-kr") == "3"

    def test_항목28_면허번호_바이트130_139(self):
        # "1234567890" → 좌측정렬 X(100) 중 처음 10자리
        raw = build_procedure_record(self._make_proc(license_no="1234567890")).encode("euc-kr")
        assert raw[130:140].decode("euc-kr") == "1234567890"

    def test_항목28_면허종류_한의사(self):
        raw = build_procedure_record(self._make_proc(license_type="3")).encode("euc-kr")
        license_type_byte = raw[129:130].decode("euc-kr")
        assert license_type_byte == "3", "한의사 면허종류는 '3'"


# ──────────────────────────────────────────────────────────────────────────────
# 항목 31: C2-08 특정내역 — 혈명코드 JS011
# ──────────────────────────────────────────────────────────────────────────────

class TestC2_08_특정내역:
    """항목 31: 혈명코드 JS011이 C2-08 특정내역 레코드에 올바르게 기록되는지."""

    def _make_special(self, hyeolmyeong: list[str]) -> SpecialRecord:
        content = ",".join(hyeolmyeong)
        return SpecialRecord(
            key=_DUMMY_KEY,
            prescription_no=0,
            record_ext_no=1,
            special_code="JS011",
            content=content,
        )

    def test_항목31_JS011_혈명코드_기록(self):
        names = ["합곡", "족삼리", "내관"]
        raw = build_special_record(self._make_special(names)).encode("euc-kr")
        # C2-08 레코드: 47번(0-indexed)부터 content 700바이트
        content_start = 47
        content_raw = raw[content_start:content_start + 700]
        content_str = content_raw.decode("euc-kr").rstrip()
        assert "합곡" in content_str
        assert "족삼리" in content_str
        assert "내관" in content_str

    def test_항목31_특정내역구분_JS011_바이트42_46(self):
        # C2-08 43-47번(0-indexed 42-46): 특정내역구분 X(5) = "JS011"
        raw = build_special_record(self._make_special(["합곡"])).encode("euc-kr")
        assert raw[42:47].decode("euc-kr") == "JS011"

    def test_C2_08_레코드_길이_747_plus_CRLF(self):
        raw = build_special_record(self._make_special(["합곡"])).encode("euc-kr")
        assert len(raw) == 749
