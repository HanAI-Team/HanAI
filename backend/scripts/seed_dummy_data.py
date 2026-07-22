"""
보안 검사 화면 캡처용 더미 운영 데이터 시딩.

목적: HIRA 보안검사(항목18~36) 스크린샷을 찍기 위해, 로그인 가능한 계정 +
각 로그/이력 화면이 "채워진 상태"로 보이도록 최소 더미를 넣는다.

실행 (반드시 dev DB 확인 후):
    cd backend
    grep "^DATABASE_URL=" .env   # elkscwboqyykae(dev) 인지 먼저 확인!
    uv run python scripts/seed_dummy_data.py

주의:
- 이 스크립트는 app.core.database.AsyncSessionLocal 을 쓰므로 .env의 DATABASE_URL을 따른다.
- crypto.py가 os.environ에서 RRN_ENCRYPTION_KEY를 직접 읽으므로, main.py와 동일하게
  맨 위에서 load_dotenv(override=True)를 호출해 .env를 os.environ에 주입한다.
- 재실행 대비: 더미 병원(name=DUMMY_HOSPITAL_NAME)과 그 하위 데이터를 지우고 새로 넣는다.

item 19 참고(정직성):
- ended_at이 채워진 "과거 종료 계정" 더미로 item 19 캡처를 가능케 하되,
  비활성화 시 ended_at 자동갱신 버그는 미수정 상태 → 코드 수정 TODO 유지.
"""

import asyncio
import os
import sys
import uuid as _uuid
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv(override=True)

from app.auth.service import pwd_context
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.models import (
    AccessControlLog,
    AccountHistory,
    AuditLog,
    DataDownloadLog,
    DataPurgeLog,
    Doctor,
    Hospital,
    LoginLog,
    PasswordHistory,
    Patient,
    StaffAccount,
    Subscription,
)
from sqlalchemy import delete, select

DUMMY_HOSPITAL_NAME = "[DUMMY] 진맥한의원"
OWNER_LICENSE = "12345678"
OWNER_PASSWORD = "Zinmac!2026"
NURSE_USERNAME = "nurse01"
NURSE_PASSWORD = "Zinmac!2026"

KST = timezone(timedelta(hours=9))


def now_kst() -> datetime:
    return datetime.now(KST)


def ts14(dt: datetime) -> str:
    return dt.strftime("%Y%m%d%H%M%S")


async def wipe_existing_dummy(db) -> None:
    result = await db.execute(
        select(Hospital.id).where(Hospital.name == DUMMY_HOSPITAL_NAME)
    )
    hospital_ids = [row[0] for row in result.all()]
    if not hospital_ids:
        return

    for hid in hospital_ids:
        await db.execute(delete(Patient).where(Patient.hospital_id == hid))
        await db.execute(delete(StaffAccount).where(StaffAccount.hospital_id == hid))
        await db.execute(delete(Subscription).where(Subscription.hospital_id == hid))
        await db.execute(delete(AccessControlLog).where(AccessControlLog.hospital_id == hid))
        await db.execute(delete(DataDownloadLog).where(DataDownloadLog.hospital_id == hid))
        await db.execute(delete(DataPurgeLog).where(DataPurgeLog.hospital_id == hid))

        doc_result = await db.execute(select(Doctor.id).where(Doctor.hospital_id == hid))
        doctor_ids = [r[0] for r in doc_result.all()]
        for did in doctor_ids:
            await db.execute(delete(LoginLog).where(LoginLog.account_id == did))
            await db.execute(delete(AccountHistory).where(AccountHistory.account_id == did))
            await db.execute(delete(PasswordHistory).where(PasswordHistory.account_id == did))
        await db.execute(delete(Doctor).where(Doctor.hospital_id == hid))
        await db.execute(delete(Hospital).where(Hospital.id == hid))

    await db.flush()


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        try:
            proj = settings.DATABASE_URL.split("postgres.")[1][:20]
        except Exception:
            proj = "(파싱 실패)"
        print(f"대상 DB project: {proj}")
        if "phdayetndkwhh" in settings.DATABASE_URL:
            print("중단: DATABASE_URL이 prod를 가리킵니다. .env를 dev로 바꾸세요.")
            return

        await wipe_existing_dummy(db)

        now = now_kst()

        hospital = Hospital(
            name=DUMMY_HOSPITAL_NAME,
            address="서울시 강남구 테스트로 1",
            phone="02-1234-5678",
            institution_code="41234567",
        )
        db.add(hospital)
        await db.flush()

        db.add(Subscription(
            hospital_id=hospital.id,
            tier="standard",
            status="active",
            staff_limit=3,
            started_at=now,
        ))

        owner = Doctor(
            hospital_id=hospital.id,
            name="김원장",
            license_number=OWNER_LICENSE,
            license_kind="한의사",
            birth_date=date(1980, 3, 15),
            password_hash=pwd_context.hash(OWNER_PASSWORD),
            role="owner",
            is_approved=True,
            is_active=True,
            approved_at=now - timedelta(days=200),
            license_verified_at=now - timedelta(days=200),
            password_changed_at=now - timedelta(days=30),
            force_password_change=False,
            chuna_training_certified=True,
            chuna_training_banner_seen=True,
        )
        db.add(owner)
        await db.flush()

        nurse = StaffAccount(
            hospital_id=hospital.id,
            name="이간호",
            username=NURSE_USERNAME,
            email="nurse01@dummy.zinmac.kr",
            password_hash=pwd_context.hash(NURSE_PASSWORD),
            role="nurse",
            is_active=True,
            password_changed_at=now - timedelta(days=10),
            force_password_change=False,
        )
        db.add(nurse)
        await db.flush()

        patients = [
            Patient(
                hospital_id=hospital.id, name="박건보", birth_date=date(1975, 5, 20),
                gender="M", phone="010-1111-2222",
                insurance_type="health", rrn="750520-1234567",
            ),
            Patient(
                hospital_id=hospital.id, name="최일종", birth_date=date(1960, 8, 8),
                gender="F", phone="010-3333-4444",
                insurance_type="medical_aid", medical_aid_grade="1", rrn="600808-2234567",
            ),
            Patient(
                hospital_id=hospital.id, name="정이종", birth_date=date(1990, 12, 1),
                gender="M", phone="010-5555-6666",
                insurance_type="medical_aid", medical_aid_grade="2", rrn="901201-1234567",
            ),
        ]
        db.add_all(patients)
        await db.flush()

        login_logs = []
        for i in range(3):
            login_logs.append(LoginLog(
                account_type="doctor", account_id=owner.id, success=False,
                ip_address="203.0.113.10", user_agent="Mozilla/5.0 (dummy)",
                attempted_at=now - timedelta(minutes=30 - i * 2),
                action="로그인 실패",
            ))
        for i in range(2):
            login_logs.append(LoginLog(
                account_type="doctor", account_id=owner.id, success=True,
                ip_address="203.0.113.10", user_agent="Mozilla/5.0 (dummy)",
                attempted_at=now - timedelta(hours=5 + i),
                action="로그인",
            ))
        login_logs.append(LoginLog(
            account_type="staff", account_id=nurse.id, success=True,
            ip_address="203.0.113.20", user_agent="Mozilla/5.0 (dummy)",
            attempted_at=now - timedelta(hours=2),
            action="로그인",
        ))
        db.add_all(login_logs)

        audit_logs = [
            AuditLog(
                table_name="patients", record_id=str(patients[0].id), action="READ",
                actor_id=owner.id, actor_type="doctor",
                changed_at=ts14(now - timedelta(hours=1)), detail="환자 상세 조회",
            ),
            AuditLog(
                table_name="patients", record_id=str(patients[1].id), action="UPDATE",
                actor_id=owner.id, actor_type="doctor",
                changed_at=ts14(now - timedelta(hours=2)), detail="연락처 수정",
            ),
            AuditLog(
                table_name="patients", record_id=str(patients[2].id), action="READ",
                actor_id=nurse.id, actor_type="staff",
                changed_at=ts14(now - timedelta(minutes=40)), detail="접수 화면 조회",
            ),
        ]
        db.add_all(audit_logs)

        access_logs = [
            AccessControlLog(
                hospital_id=hospital.id, target_account_id=nurse.id, target_account_type="staff",
                role="nurse", action_type="부여", reason="입사",
                acted_at=ts14(now - timedelta(days=60)), acted_by=owner.id,
            ),
            AccessControlLog(
                hospital_id=hospital.id, target_account_id=nurse.id, target_account_type="staff",
                role="receptionist", action_type="변경", reason="조직변경",
                acted_at=ts14(now - timedelta(days=5)), acted_by=owner.id,
            ),
        ]
        db.add_all(access_logs)

        db.add(AccountHistory(
            account_type="doctor", account_id=owner.id, action="created",
            actor_id=None, started_at=now - timedelta(days=200), ended_at=None,
            detail="원장 계정 생성",
        ))
        db.add(AccountHistory(
            account_type="staff", account_id=nurse.id, action="created",
            actor_id=owner.id, started_at=now - timedelta(days=60), ended_at=None,
            detail="간호사 계정 생성",
        ))
        past_staff_id = _uuid.uuid4()
        db.add(AccountHistory(
            account_type="staff", account_id=past_staff_id, action="created",
            actor_id=owner.id,
            started_at=now - timedelta(days=400), ended_at=now - timedelta(days=90),
            detail="전 간호사 계정 생성",
        ))
        db.add(AccountHistory(
            account_type="staff", account_id=past_staff_id, action="deactivated",
            actor_id=owner.id,
            started_at=now - timedelta(days=90), ended_at=now - timedelta(days=90),
            detail="퇴사 처리",
        ))

        db.add(PasswordHistory(
            account_type="doctor", account_id=owner.id,
            password_hash=pwd_context.hash("OldPass!2025"),
        ))
        db.add(PasswordHistory(
            account_type="doctor", account_id=owner.id,
            password_hash=owner.password_hash,
        ))

        db.add(DataDownloadLog(
            hospital_id=hospital.id, doctor_id=owner.id,
            download_type="patient_list", reason="월말 청구 대상 환자 명단 확인",
            ip_address="203.0.113.10",
        ))

        db.add(DataPurgeLog(
            hospital_id=hospital.id, doctor_id=owner.id, patient_id=None,
            patient_name_before="홍파기", reason="보유기간(진료기록 10년) 경과 자동 파기",
            purge_type="anonymize", purged_at=ts14(now - timedelta(days=1)),
        ))
        db.add(DataPurgeLog(
            hospital_id=hospital.id, doctor_id=owner.id, patient_id=None,
            patient_name_before="김만료", reason="처방전 보유기간(3년) 경과 파기",
            purge_type="delete", purged_at=ts14(now - timedelta(days=2)),
        ))

        await db.commit()

        print("\n더미 시딩 완료")
        print(f"  병원: {DUMMY_HOSPITAL_NAME}")
        print(f"  원장 로그인:   면허번호 {OWNER_LICENSE} / 비번 {OWNER_PASSWORD}")
        print(f"  간호사 로그인: username {NURSE_USERNAME} / 비번 {NURSE_PASSWORD}")
        print("  환자 3, LoginLog 6, AuditLog 3, AccessControlLog 2, AccountHistory 4,")
        print("  PasswordHistory 2, DataDownloadLog 1, DataPurgeLog 2")
        print("\n  item 19: 종료계정 더미로 캡처 가능하나 ended_at 자동갱신 버그는 미수정 (TODO).")


if __name__ == "__main__":
    asyncio.run(seed())