import os

# DATABASE_URL must be set before any app module is imported
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from datetime import datetime, timezone
from uuid import UUID
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.auth.service import create_access_token
from app.core.database import Base, get_db
from app.core.models import Doctor, Hospital, Subscription, KcdUCode
from datetime import date
from main import app
from app.core.models import FeeMaster

TEST_ENGINE = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TEST_SESSION = async_sessionmaker(
    TEST_ENGINE, class_=AsyncSession, expire_on_commit=False
)


@pytest_asyncio.fixture
async def _tables():
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db(_tables):
    async with TEST_SESSION() as session:
        yield session


@pytest_asyncio.fixture
async def client(_tables):
    async def override_get_db():
        async with TEST_SESSION() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def approved_doctor(db, client):
    """DB에 승인된 의사를 생성하고 (doctor, auth_headers)를 반환."""
    hospital = Hospital(name="테스트의원")
    db.add(hospital)
    await db.flush()

    doctor = Doctor(
        hospital_id=hospital.id,
        name="홍길동",
        license_number="12345678",
        password_hash="hashed_password",
        is_approved=True,
        approved_at=datetime.now(timezone.utc),
    )
    db.add(doctor)
    await db.flush()

    db.add(Subscription(hospital_id=hospital.id, tier="basic", status="active"))
    await db.commit()
    await db.refresh(doctor)

    token = create_access_token(
        UUID(str(doctor.id)), UUID(str(doctor.hospital_id)), str(doctor.role)
    )
    return doctor, {"Authorization": f"Bearer {token}"}

@pytest_asyncio.fixture
async def kcd_codes(db):
    """테스트용 KCD 코드 픽스처."""
    codes = [
        KcdUCode(code="A001", korean_name="콜레라", effective_date=date(2000, 1, 1), expired_date=None, sex_restriction=None, is_notifiable=True),
        KcdUCode(code="B001", korean_name="장티푸스", effective_date=date(2000, 1, 1), expired_date=None, sex_restriction=None, is_notifiable=False),
        KcdUCode(code="Z999", korean_name="만료된코드", effective_date=date(2000, 1, 1), expired_date=date(2020, 12, 31), sex_restriction=None, is_notifiable=False),
        KcdUCode(code="M001", korean_name="남성전용질환", effective_date=date(2000, 1, 1), expired_date=None, sex_restriction="M", is_notifiable=False),
        KcdUCode(code="F001", korean_name="여성전용질환", effective_date=date(2000, 1, 1), expired_date=None, sex_restriction="F", is_notifiable=False),
    ]
    db.add_all(codes)
    await db.commit()
    return codes

@pytest_asyncio.fixture
async def fee_master_codes(db):
    """테스트용 FeeMaster 픽스처."""
    codes = [
        FeeMaster(code="40121", name="이침술", category="분구침술", unit_price=1000, is_standalone=True, is_insured=True, insured_health=True, insured_medical_aid=True, insured_veterans=False),
        FeeMaster(code="40122", name="두침술", category="분구침술", unit_price=1000, is_standalone=True, is_insured=True, insured_health=True, insured_medical_aid=True, insured_veterans=False),
        FeeMaster(code="40001", name="체침술", category="침술", unit_price=1000, is_standalone=False, is_insured=True, insured_health=True, insured_medical_aid=True, insured_veterans=False),
        FeeMaster(code="AA159", name="체침 단순침술", category="침술", unit_price=1000, is_standalone=False, is_insured=True, insured_health=True, insured_medical_aid=True, insured_veterans=False),
        FeeMaster(code="AA161", name="전침", category="침술", unit_price=1000, is_standalone=False, is_insured=True, insured_health=True, insured_medical_aid=True, insured_veterans=False),
        FeeMaster(code="AA163", name="도침", category="침술", unit_price=1000, is_standalone=False, is_insured=True, insured_health=True, insured_medical_aid=True, insured_veterans=False),
        FeeMaster(code="AA165", name="화침", category="침술", unit_price=1000, is_standalone=False, is_insured=True, insured_health=True, insured_medical_aid=True, insured_veterans=False),
    ]
    db.add_all(codes)
    await db.commit()
    return codes
