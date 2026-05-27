from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

_db_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(_db_url, echo=False, connect_args={"statement_cache_size": 0})

Base = declarative_base()

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
