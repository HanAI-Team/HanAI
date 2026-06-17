"""
KCD8 한방 U코드 시드 스크립트

실행: cd backend && python scripts/seed_kcd.py
"""
import asyncio
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from app.core.config import settings
from app.core.models import KcdUCode

CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "kcd8_u_codes.csv")


async def seed():
    db_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(db_url, echo=False, connect_args={"statement_cache_size": 0})
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        result = await session.execute(text("SELECT COUNT(*) FROM kcd_u_codes"))
        count = result.scalar()
        if count > 0:
            print(f"이미 {count}개의 코드가 있습니다. 덮어쓰려면 테이블을 비우고 다시 실행하세요.")
            return

        from datetime import date as date_type

        def _parse_date(val: str):
            val = val.strip()
            if not val:
                return None
            try:
                return date_type.fromisoformat(val)
            except ValueError:
                return None

        rows = []
        with open(CSV_PATH, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(KcdUCode(
                    code=row["code"].strip(),
                    korean_name=row["korean_name"].strip(),
                    hanja=row.get("hanja", "").strip() or None,
                    category=row.get("category", "").strip() or None,
                    effective_date=_parse_date(row.get("effective_date", "")),
                    expired_date=_parse_date(row.get("expired_date", "")),
                ))

        session.add_all(rows)
        await session.commit()
        print(f"✓ {len(rows)}개 KCD8 U코드 적재 완료")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
