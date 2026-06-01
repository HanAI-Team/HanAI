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
from app.core.models import Doctor, Hospital, Subscription
from main import app

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
        is_approved=True,
        approved_at=datetime.now(timezone.utc),
    )
    db.add(doctor)
    await db.flush()

    db.add(Subscription(doctor_id=doctor.id, tier="basic", status="active"))
    await db.commit()
    await db.refresh(doctor)

    token = create_access_token(
        UUID(str(doctor.id)), UUID(str(doctor.hospital_id)), str(doctor.role)
    )
    return doctor, {"Authorization": f"Bearer {token}"}
