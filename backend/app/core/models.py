import uuid

from app.core.crypto import EncryptedString
from app.core.database import Base
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


# ================================================================
# 병원 / 인증 / 계정
# ================================================================
class Hospital(Base):
    __tablename__ = "hospitals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    address = Column(String)
    phone = Column(String)
    institution_code = Column(String(8), nullable=True)  # 심평원 요양기관기호
    agency_code = Column(String(5), nullable=True)  # 대행청구단체기호 (EDI 레코드1 pos342-346)
    approval_no = Column(String(35), nullable=True)  # 소프트웨어 승인번호
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    doctors = relationship("Doctor", back_populates="hospital")
    staff_accounts = relationship("StaffAccount", back_populates="hospital")
    patients = relationship("Patient", back_populates="hospital")
    medical_records = relationship("MedicalRecord", back_populates="hospital")
    subscription = relationship("Subscription", back_populates="hospital", uselist=False)
    

class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey("hospitals.id"), nullable=False)
    name = Column(String, nullable=False)
    license_number = Column(String, unique=True, nullable=False)
    license_kind = Column(String)
    birth_date = Column(Date, nullable=True)  # 데이터허브 면허인증 시 주민번호에서 추출해 저장
    password_hash = Column(String, nullable=False)
    role = Column(String, default="owner")
    is_approved = Column(Boolean, default=False, nullable=False)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    license_verified_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    password_changed_at = Column(DateTime(timezone=True), nullable=True)
    force_password_change = Column(Boolean, default=False, nullable=False, server_default="false")

    # 추나요법 급여 사전교육(대한한의사협회, 온라인9시간+오프라인6시간=15시간) 이수 여부.
    # 일회성 교육으로 확인되어(2026-07-08, 승희 확인) 만료/재이수 로직은 별도로 두지 않음.
    # 원장 본인이 프로필 화면에서 직접 체크(PATCH /auth/me)하는 방식. 미이수 상태로
    # 추나요법을 청구하면 notice_rules.py에서 ERROR로 차단됨.
    chuna_training_certified = Column(Boolean, default=False, nullable=False, server_default="false")
    # 배포 직후 "이수 여부를 확인해주세요" 안내를 1회만 띄우기 위한 플래그.
    # chuna_training_certified와 별개로 관리해야 함 — 안내를 보고 "나는 미이수"라고
    # 확인한 원장도 certified=False로 남지만, banner_seen=True가 되어 매번 로그인할
    # 때마다 배너가 다시 뜨는 걸 막는다.
    chuna_training_banner_seen = Column(Boolean, default=False, nullable=False, server_default="false")

    hospital = relationship("Hospital", back_populates="doctors")
    medical_records = relationship("MedicalRecord", back_populates="doctor")
    feedbacks = relationship("Feedback", back_populates="doctor")



class SaturdayHolidayStaffing(Base):
    """MT050(토요일·공휴일 근무현황) 산출용"""
    __tablename__ = "saturday_holiday_staffing"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey("hospitals.id"), nullable=False)
    work_date = Column(Date, nullable=False)
    doctor_count = Column(Numeric(3, 1), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    hospital = relationship("Hospital")

    __table_args__ = (UniqueConstraint("hospital_id", "work_date", name="uq_sat_holiday_staffing_date"),)


class DoctorWorkDays(Base):
    __tablename__ = "doctor_work_days"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey("hospitals.id"), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctors.id"), nullable=True)
    claim_period_year = Column(Integer, nullable=False)   # 청구년도
    claim_period_month = Column(Integer, nullable=False)  # 청구월
    doctor_birth_date = Column(String(6), nullable=False) # 의사 생년월일 YYMMDD
    work_days = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "hospital_id", "claim_period_year", "claim_period_month", "doctor_id",
            name="uq_doctor_work_days_period_doctor",
        ),
    )


class StaffAccount(Base):
    __tablename__ = "staff_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey("hospitals.id"), nullable=False)
    name = Column(String, nullable=False)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="nurse")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    password_changed_at = Column(DateTime(timezone=True), nullable=True)
    force_password_change = Column(Boolean, default=False, nullable=False, server_default="false")

    hospital = relationship("Hospital", back_populates="staff_accounts")


# ================================================================
# 구독 / 결제
# ================================================================
class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey("hospitals.id"), unique=True, nullable=False)
    tier = Column(String, default="basic")
    status = Column(String, default="active")
    staff_limit = Column(Integer, default=2)
    started_at = Column(DateTime(timezone=True))
    expired_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    hospital = relationship("Hospital", back_populates="subscription")


# ================================================================
# 환자 / 산정특례
# ================================================================
class Patient(Base):
    __tablename__ = "patients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey("hospitals.id"), nullable=False)
    name = Column(String, nullable=False)
    birth_date = Column(Date)
    gender = Column(String)
    phone = Column(String)
    memo = Column(Text)
    insurance_type = Column(String, default="health")
    medical_aid_grade = Column(String(1), nullable=True)   # 의료급여 1종="1", 2종="2", 나머지 None
    disability_grade = Column(String(1), nullable=True)    # 장애 등급 "1"~"6", None이면 비해당

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    rrn = Column(EncryptedString(500), nullable=True)
    confirmation_no = Column(String(13), nullable=True)
    hospital = relationship("Hospital", back_populates="patients")
    medical_records = relationship("MedicalRecord", back_populates="patient")
    special_case_registrations = relationship("SpecialCaseRegistration", back_populates="patient")


class SpecialCaseRegistration(Base):
    """산정특례 등록 이력. 환자당 다건 가능(암+희귀난치 동시 등록 등)."""
    __tablename__ = "special_case_registrations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)

    special_code = Column(String(4), nullable=False)  # 특정기호. V193=암, V027=희귀난치, V221=중증화상 등
    category = Column(String(20), nullable=False)     # 암 / 결핵 / 뇌혈관 / 심장 / 신체기능저하군
    registered_disease_code = Column(String(10), nullable=True)  # 등록 상병코드 (KCD/ICD). MT028 기재 시 '유사상병코드' 역할

    # MT028: KCD 코드가 없는 희귀질환 등의 실제 상병명 (예: "가족성선종성폴립증").
    # 값이 있으면 EDI C2-08에 MT028 레코드를 추가하며, 내용은 "<registered_disease_code>/<disease_name>" 형태.
    disease_name = Column(String(100), nullable=True)

    # MT014: 건보공단 발급 산정특례 등록번호 (예: "01-24-00012345").
    # 값이 있으면 EDI C2-08에 MT014 레코드를 추가.
    registration_number = Column(String(20), nullable=True)

    # V810(중증치매 일반) 전용 사전승인번호. 형태: "구분(1자리)-차수별연도(2자리)-일련번호"
    # V810 청구 시 registration_number 대신 이 값을 MT014에 기재.
    # None이면 공단 사전승인 미완료 상태로 간주해 needs_review=True 강제.
    prior_approval_number = Column(String(30), nullable=True)

    registered_at = Column(Date, nullable=False)
    expires_at = Column(Date, nullable=True)  # NULL 허용: 결핵 등 이벤트(완치/사망/진단변경) 기반 종료는 날짜로 못 정함
    status = Column(String(10), nullable=False, default="active")  # active / cancelled (수동 취소 전용. expired는 조회 시점에 expires_at으로 동적 판단)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())

    patient = relationship("Patient", back_populates="special_case_registrations")


# ================================================================
# 청구
# ================================================================
class Claim(Base):
    __tablename__ = "claims"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctors.id"), nullable=False)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey("hospitals.id"), nullable=False)
    claim_period_year = Column(Integer, nullable=False)
    claim_period_month = Column(Integer, nullable=False)
    # 청구구분: null=최초, "supplement"=보완, "addition"=추가
    # ※ kmishe_writer.py의 claim_type(보험자종별: 건강보험/의료급여/보훈)과는 무관한 별개 필드
    claim_type = Column(String, nullable=True)
    original_receipt_no = Column(Integer, nullable=True)      # 당초 청구명세서 접수번호 (보완·추가청구 시)
    original_record_serial = Column(Integer, nullable=True)   # 명일련 (보완·추가청구 시)
    rejection_reason_code = Column(String(2), nullable=True)  # 심사불능사유코드 (보완청구 시만)
    total_amount = Column(Integer, nullable=False, default=0)
    patient_copay = Column(Integer, nullable=False, default=0)
    claim_amount = Column(Integer, nullable=False, default=0)
    non_benefit_total = Column(Integer, nullable=False, default=0)         # 비급여 총액 (C2-11 benefit_total_2 산출용)
    disability_medical_aid = Column(Integer, nullable=False, default=0)  # C2-11 장애인의료비
    support_fund = Column(Integer, nullable=False, default=0)             # C2-11 지원금
    differential_index = Column(Numeric(5, 2), default=1.0)
    status = Column(String, nullable=False, default="draft")
    special_case_review_reason = Column(String(100), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    approval_no = Column(String(35), nullable=True)  # 검사승인번호 an(35)
    warn_notices = Column(JSON, nullable=True)

    medical_records = relationship("MedicalRecord", back_populates="claim")
    line_items = relationship("ClaimLineItem", back_populates="claim", cascade="all, delete-orphan")
    patient = relationship("Patient", foreign_keys=[patient_id])


class ClaimSequence(Base):
    """청구번호(SAM/EDI H010 7-16, an(10) = 진료년월6 + 일련번호4) 뒷자리 4자리
    일련번호를 병원+진료년월 조합별로 관리하는 카운터.

    같은 달에 여러 번 청구서를 만들어야 하는 경우(보완·추가청구로 인한
    재전송, 상시점검 재시험, 다병원 확장 등) 매번 겹치지 않는 번호를 내주기
    위해 둔다. last_serial은 INSERT ... ON CONFLICT DO UPDATE ...
    RETURNING 한 문장으로 원자적으로 증가시켜 동시 요청에도 중복이 나지
    않게 한다(app.billing.service.next_claim_serial 참고).
    """
    __tablename__ = "claim_sequences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey("hospitals.id"), nullable=False)
    claim_period_year = Column(Integer, nullable=False)
    claim_period_month = Column(Integer, nullable=False)
    last_serial = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint(
            "hospital_id", "claim_period_year", "claim_period_month",
            name="uq_claim_sequence_hospital_period",
        ),
    )


class ClaimResubmissionHistory(Base):
    """보완·추가청구 처리 이력 (append-only). PATCH 호출마다 한 줄씩 쌓인다."""
    __tablename__ = "claim_resubmission_histories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_id = Column(UUID(as_uuid=True), ForeignKey("claims.id"), nullable=False)
    actor_id = Column(UUID(as_uuid=True), nullable=True)  # Doctor 또는 StaffAccount — FK 미설정(AccountHistory와 동일 패턴)
    claim_type = Column(String, nullable=False)          # "supplement" | "addition"
    receipt_no = Column(Integer, nullable=True)
    record_serial = Column(Integer, nullable=True)
    reason_code = Column(String(2), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ClaimRejectionCode(Base):
    """요양급여비용 심사보류·불능 및 반송 사유별 코드 (별첨6), 수탁기관 통보 사유코드 (별첨7).

    category="반송"|"심사불능"|"수탁기관통보". detail_code=""(빈 문자열)이면 상위 코드
    자체의 포괄 설명(세부코드 없는 행), 별첨7은 세부코드 구조가 없어 항상 "".
    (NULL 대신 ""을 쓰는 이유: Postgres 유니크 제약은 NULL끼리 서로 다른 값으로 취급해
    재시딩 시 ON CONFLICT가 매칭되지 않기 때문.)
    """
    __tablename__ = "claim_rejection_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(10), nullable=False)
    code = Column(String(2), nullable=False)
    detail_code = Column(String(2), nullable=False, server_default="")
    description = Column(String(500), nullable=False)

    __table_args__ = (
        UniqueConstraint("category", "code", "detail_code", name="uq_claim_rejection_code"),
    )


class ClaimLineItem(Base):
    """차트 화면에서 항목 클릭 시 생성되는 청구 라인. EDI C2-71과 1:1 대응."""

    __tablename__ = "claim_line_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_id = Column(UUID(as_uuid=True), ForeignKey("claims.id"), nullable=False)
    medical_record_id = Column(UUID(as_uuid=True), ForeignKey("medical_records.id"), nullable=False)

    hang = Column(String(2), nullable=False)
    mok = Column(String(2), nullable=False)
    code = Column(String(9), nullable=False)
    name = Column(String(50), nullable=False)

    unit_price = Column(Numeric(10, 2), nullable=False, default=0)
    qty = Column(Numeric(5, 2), nullable=False, default=1)
    days = Column(Integer, nullable=False, default=1)
    amount = Column(Integer, nullable=False, default=0)

    hyeolmyeong_names = Column(JSON, nullable=True)  # DEPRECATED — 레거시 조회 전용, 신규 저장 금지
    is_non_benefit = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    claim = relationship("Claim", back_populates="line_items")
    acupoints = relationship(
        "ClaimLineItemAcupoint",
        back_populates="line_item",
        cascade="all, delete-orphan",
        order_by="ClaimLineItemAcupoint.display_order",
    )


class ClaimLineItemAcupoint(Base):
    """청구 라인(ClaimLineItem)과 경혈 마스터(AcupuncturePoint)를 연결하는 다대다 조인 테이블.

    korean_name은 AcupuncturePoint.korean_name의 스냅샷이다 (ClaimLineItem.name이
    FeeMaster.name을 그대로 복사해 저장하는 기존 패턴과 동일 — 마스터가 나중에
    바뀌어도 실제 청구 당시 표기가 그대로 남아야 하므로 FK만 두지 않고 이름도 같이 저장).
    """

    __tablename__ = "claim_line_item_acupoints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    claim_line_item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("claim_line_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    acupuncture_point_code = Column(
        String(10), ForeignKey("acupuncture_points.code"), nullable=False
    )
    korean_name = Column(String(50), nullable=False)  # 청구 당시 경혈명 스냅샷 (화면 표시용)
    display_order = Column(Integer, nullable=False, default=0)  # 입력 순서 보존
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "claim_line_item_id", "acupuncture_point_code",
            name="uq_line_item_acupoint",
        ),
    )

    line_item = relationship("ClaimLineItem", back_populates="acupoints")
    acupuncture_point = relationship("AcupuncturePoint", foreign_keys=[acupuncture_point_code])


# ================================================================
# 진료 기록 / AI
# ================================================================
class MedicalRecord(Base):
    __tablename__ = "medical_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctors.id"), nullable=False)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey("hospitals.id"), nullable=False)
    claim_id = Column(UUID(as_uuid=True), ForeignKey("claims.id"), nullable=True)
    raw_transcription = Column(Text)
    chart_structured = Column(Text)
    audio_file_url = Column(String)
    status = Column(String, default="recording")
    kcd_code = Column(String(10), nullable=True)  # KCD 상병코드 (EDI C2-02)
    recorded_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    medical_history = Column(Text, nullable=True)
    selected_result = Column(String, nullable=True)

    patient = relationship("Patient", back_populates="medical_records")
    doctor = relationship("Doctor", back_populates="medical_records")
    hospital = relationship("Hospital", back_populates="medical_records")
    claim = relationship("Claim", back_populates="medical_records")
    ai_result = relationship("AIResult", back_populates="medical_record", uselist=False, cascade="all, delete-orphan")
    prescriptions = relationship("Prescription", back_populates="medical_record", cascade="all, delete-orphan")
    procedures = relationship("MedicalRecordProcedure", back_populates="medical_record", cascade="all, delete-orphan")


class AIResult(Base):
    __tablename__ = "ai_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    medical_record_id = Column(UUID(as_uuid=True), ForeignKey("medical_records.id"), unique=True, nullable=False)
    diagnosis_suggestion = Column(Text)
    constitution_result = Column(Text)
    prescription_suggestion = Column(Text)
    acupuncture_suggestion = Column(Text)
    reasoning = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    medical_record = relationship("MedicalRecord", back_populates="ai_result")
    feedbacks = relationship("Feedback", back_populates="ai_result")


class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ai_result_id = Column(UUID(as_uuid=True), ForeignKey("ai_results.id"), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctors.id"), nullable=False)
    category = Column(String)
    score = Column(Integer)
    comment = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ai_result = relationship("AIResult", back_populates="feedbacks", uselist=False)
    doctor = relationship("Doctor", back_populates="feedbacks")


class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    medical_record_id = Column(UUID(as_uuid=True), ForeignKey("medical_records.id"), nullable=False)
    prescription_name = Column(String)
    ingredients = Column(Text)
    dosage = Column(String)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    prescription_type = Column(String, nullable=True)
    adjustment_type = Column(String, nullable=True)
    formula_code = Column(String, nullable=True)
    unit_price = Column(Integer, default=0)
    daily_dosage_ratio = Column(Numeric(4, 2), default=1.0)
    total_dosage_days = Column(Integer, default=0)
    total_dosage_price = Column(Integer, default=0)
    species_count = Column(Integer, default=0)
    total_weight_g = Column(Numeric(8, 2), default=0)
    low_cost_substitute = Column(Boolean, default=False)
    low_cost_surcharge = Column(Integer, default=0)
    dispensing_fee = Column(Integer, default=0)

    medical_record = relationship("MedicalRecord", back_populates="prescriptions")


class MedicalRecordProcedure(Base):
    __tablename__ = "medical_record_procedures"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    medical_record_id = Column(UUID(as_uuid=True), ForeignKey("medical_records.id", ondelete="CASCADE"), nullable=False)
    procedure_type = Column(String, nullable=False)
    details = Column(JSON, nullable=True)
    amount = Column(Integer, default=0)
    is_non_benefit = Column(Boolean, nullable=False, default=False)  # 비급여이면 non_benefit_total에 합산
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # EDI 명세서진료내역 필수 필드
    hang          = Column(String(2),  nullable=True)               # 항번호 (04=시술및처치료)
    mok           = Column(String(2),  nullable=True)               # 목번호 (01=침술 02=구술 03=부항 04=처치 99=기타)
    code_gubun    = Column(String(1),  nullable=True, default="A")  # 코드구분 (A=수가 B=전용 C=약가 H=치료재료)
    unit_price    = Column(Numeric(12, 2), nullable=True)           # 단가
    qty           = Column(Numeric(7, 2),  nullable=True)           # 1일투여량/실시횟수
    days          = Column(Integer,    nullable=True)               # 총투여일수/실시횟수
    license_type  = Column(String(1),  nullable=True, default="3") # 면허종류 (3=한의사)
    license_no    = Column(String(10), nullable=True)              # 면허번호
    special_detail = Column(String(700), nullable=True)            # 특정내역 (JS011 혈명코드 등)
    fee_master_code = Column(String(20), ForeignKey("fee_master.code"), nullable=True)

    # C2-13 명세서진료내역(의치과및한방) 필드
    prescription_days = Column(Integer, default=0, nullable=True)           # 처방일수
    copay_rate_code = Column(String(2), default="D", nullable=True)         # 본인부담률구분코드
    prescription_issue_date = Column(String(8), nullable=True)              # 처방전발급일자
    prescription_serial = Column(Integer, default=0, nullable=True)         # 처방전일련번호
    adjustment_type = Column(String(10), nullable=True)                     # 가감등구분

    medical_record = relationship("MedicalRecord", back_populates="procedures")
    fee_master = relationship("FeeMaster", foreign_keys="[MedicalRecordProcedure.fee_master_code]")


# ================================================================
# 보안 / 로그
# ================================================================
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    table_name = Column(String(50), nullable=False)
    record_id = Column(String(36), nullable=False)
    action = Column(String(10), nullable=False)
    actor_id = Column(UUID(as_uuid=True), nullable=True)
    actor_type = Column(String(20), nullable=True)
    changed_at = Column(String(14), nullable=False)
    detail = Column(Text, nullable=True)


class DataDownloadLog(Base):
    """개인정보 CSV 다운로드 사유 기록 (HIRA 인증 체크리스트 대응)."""
    __tablename__ = "data_download_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey("hospitals.id"), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), nullable=True)
    download_type = Column(String(50), nullable=False)  # "patient_list" / "medical_records"
    reason = Column(String(500), nullable=False)
    ip_address = Column(String(45), nullable=True)
    downloaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DataPurgeLog(Base):
    __tablename__ = "data_purge_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey("hospitals.id"), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctors.id"), nullable=False)
    patient_id = Column(UUID(as_uuid=True), nullable=True)  # 익명화 후 참조 불가할 수 있음
    patient_name_before = Column(String, nullable=True)  # 파기 전 이름 보존
    reason = Column(String, nullable=False)
    purge_type = Column(String, nullable=False, default="anonymize")  # anonymize | delete
    purged_at = Column(String, nullable=False)  # YYYYMMDDHHMMSS (기존 audit_logs 패턴)


# ================================================================
# 수가 / 코드 마스터
# ================================================================
class AcupuncturePoint(Base):
    __tablename__ = "acupuncture_points"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True, nullable=False, index=True)
    korean_name = Column(String(50), nullable=False)
    meridian = Column(String(30), nullable=True)
    location = Column(Text, nullable=True)
    is_standalone = Column(Boolean, default=False, nullable=False)
    forbidden_with = Column(JSON, nullable=True)


class KcdUCode(Base):
    __tablename__ = "kcd_u_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    korean_name = Column(String(150), nullable=False)
    hanja = Column(String(100))
    category = Column(String(100))
    effective_date = Column(Date, nullable=True)
    expired_date = Column(Date, nullable=True)
    sex_restriction = Column(String(1), nullable=True)   # "M"=남성만, "F"=여성만, None=제한없음
    is_notifiable = Column(Boolean, default=False)        # 법정감염병 여부


class FeeMaster(Base):
    """한방 행위코드 수가 마스터 (HIRA 요양급여비용 목록표 기준)."""

    __tablename__ = "fee_master"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False, index=True)   # 행위코드
    name = Column(String(100), nullable=False)                            # 행위명
    category = Column(String(20), nullable=False)                         # 침술/뜸/부항/추나
    insured_health      = Column(Boolean, nullable=False, server_default="true")   # 건강보험(4) 적용 여부
    insured_medical_aid = Column(Boolean, nullable=False, server_default="true")   # 의료급여(5) 적용 여부
    insured_veterans    = Column(Boolean, nullable=False, server_default="false")  # 보훈(7) 적용 여부
    unit_price = Column(Integer, nullable=False)                          # 수가 (원, 건강보험 기준)
    is_insured = Column(Boolean, default=True, nullable=False)            # 급여 여부
    effective_date = Column(Date, nullable=True)
    expired_date = Column(Date, nullable=True)
    is_standalone = Column(Boolean, default=False, nullable=False, server_default="false")


class DrugMaster(Base):
    """약제급여목록 및 급여상한금액표 (HIRA, 매월 고시). 전국 공통(양·한방 구분 없음)."""

    __tablename__ = "drug_master"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_code = Column(String(20), unique=True, nullable=False, index=True)   # 제품코드
    product_name = Column(String(300), nullable=False)                            # 제품명
    ingredient_code = Column(String(20), nullable=True)                           # 주성분코드
    ingredient_name = Column(String(1500), nullable=True)                         # 주성분명
    company_name = Column(String(100), nullable=True)                            # 업체명
    spec = Column(String(50), nullable=True)                                      # 규격
    unit = Column(String(30), nullable=True)                                      # 단위
    unit_price = Column(Integer, nullable=False)                                  # 상한금액표 금액(원)
    administration_route = Column(String(20), nullable=True)                      # 투여 (내복/외용/주사/기타)
    classification_code = Column(String(10), nullable=True)                       # 분류(식약분류) 코드
    # 전문/일반 구분. 원본 엑셀 헤더는 이 컬럼을 "전일"이라고 표기하지만 실제
    # 값은 항상 "전문"|"일반"이라 헤더 자체가 오기임 — 값 기준으로 매핑.
    is_prescription = Column(Boolean, nullable=True)
    effective_date = Column(Date, nullable=True)                                  # 고시 적용일 (파일 스냅샷 기준)


# ================================================================
# 보안 / 로그
# ================================================================
class AccountHistory(Base):
    __tablename__ = "account_histories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_type = Column(String, nullable=False)  # "doctor" | "staff"
    account_id = Column(UUID(as_uuid=True), nullable=False)
    action = Column(String, nullable=False)  # "created" | "deactivated" | "role_changed"
    actor_id = Column(UUID(as_uuid=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
    detail = Column(Text, nullable=True)


class LoginLog(Base):
    __tablename__ = "login_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_type = Column(String, nullable=False)  # "doctor" | "staff"
    account_id = Column(UUID(as_uuid=True), nullable=True)
    success = Column(Boolean, nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    attempted_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class PasswordHistory(Base):
    __tablename__ = "password_histories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_type = Column(String, nullable=False)
    account_id = Column(UUID(as_uuid=True), nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())



# ================================================================
# 접수 (DailyQueue)
# ================================================================
class DailyQueue(Base):
    __tablename__ = "daily_queue"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey("hospitals.id"), nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctors.id"), nullable=True)
    queue_date = Column(Date, nullable=False)
    checked_in_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    # waiting(대기) -> in_progress(진료중) -> billed(처치·수납대기, 청구 저장 완료) -> paid(수납완료)
    status = Column(String(20), nullable=False, default="waiting")
    source = Column(String(20), nullable=False, default="manual")
    assigned_bed = Column(String(20), nullable=True)  # 베드 배정 (자유 입력, 예: "1번", "A실")
    claim_id = Column(UUID(as_uuid=True), ForeignKey("claims.id"), nullable=True)  # 청구 모달에서 생성된 청구
    # UniqueConstraint 없음

    patient = relationship("Patient", lazy="raise")


class ClaimPayment(Base):
    """환자 진료비 수납 기록. Claim 1건에 보통 1건이지만 분할수납 가능성을 고려해 1:N."""
    __tablename__ = "claim_payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey("hospitals.id"), nullable=False)
    claim_id = Column(UUID(as_uuid=True), ForeignKey("claims.id"), nullable=False)
    method = Column(String(20), nullable=False)  # cash | card | transfer
    amount = Column(Integer, nullable=False)
    paid_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    processed_by_name = Column(String, nullable=False)  # 수납 처리한 계정 이름 (조회용, 비정규화)

    claim = relationship("Claim")


# ================================================================
# 구독 / 결제
# ================================================================
class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey("hospitals.id"), nullable=False)
    order_id = Column(String(100), unique=True, nullable=False)
    payment_key = Column(String(200), nullable=True)
    tier = Column(String(20), nullable=False)
    billing_period = Column(String(10), nullable=False)
    amount = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    # pending / paid / failed / refunded
    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)