"""KCD-8 전체 상병분류기호 시딩 스크립트 (심평원 요양기관업무포털 공식 데이터셋).

- 기존 kcd_u_codes 테이블(U코드 137개 + 공통코드 95개)의 category/hanja는
  그대로 유지하고, korean_name/effective_date/expired_date/sex_restriction/
  is_notifiable은 CSV 공식 데이터로 갱신한다(ON CONFLICT DO UPDATE).
  나머지 코드는 신규 삽입한다.
- 불완전코드(3~5자리 분류 상위 항목, 청구 불가)는 시딩하지 않는다.
- 동일 상병기호가 여러 행(동의어/색인어)으로 나오는 경우, 파일에 먼저
  나오는 행을 대표 명칭으로 채택한다(청크 내 dedup + DB단 ON CONFLICT DO UPDATE
  로 청크 간 dedup도 마지막 처리된 값으로 수렴됨).

실행: cd backend && python scripts/seed_kcd_full.py
"""
import asyncio
import os
import sys
from datetime import date as date_type

import pandas as pd
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.models import KcdUCode

CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "kcd_full.csv")
CHUNK_SIZE = 1000

COLUMNS = [
    "code", "effective_date", "expired_date", "korean_name", "english_name",
    "complete_flag", "main_use", "notifiable_grade", "sex", "age_max", "age_min", "division",
]

SEX_MAP = {"남": "M", "여": "F"}


def _parse_date(val: str):
    val = (val or "").strip()
    if not val:
        return None
    try:
        return date_type.fromisoformat(val)
    except ValueError:
        return None


def _rows_from_chunk(chunk: pd.DataFrame):
    chunk = chunk[chunk["complete_flag"] == "완전코드"]
    chunk = chunk.drop_duplicates(subset="code", keep="first")

    rows = []
    for r in chunk.itertuples(index=False):
        rows.append({
            "code": r.code.strip(),
            "korean_name": r.korean_name.strip(),
            "effective_date": _parse_date(r.effective_date),
            "expired_date": _parse_date(r.expired_date),
            "sex_restriction": SEX_MAP.get((r.sex or "").strip()),
            "is_notifiable": bool((r.notifiable_grade or "").strip()),
        })
    return rows


async def seed():
    db_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(db_url, echo=False, connect_args={"statement_cache_size": 0})
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    total_affected = 0
    async with async_session() as session:
        before = (await session.execute(text("SELECT COUNT(*) FROM kcd_u_codes"))).scalar()

        reader = pd.read_csv(
            CSV_PATH, encoding="utf-8-sig", dtype=str, keep_default_na=False,
            names=COLUMNS, header=0, chunksize=CHUNK_SIZE,
        )
        for chunk in reader:
            rows = _rows_from_chunk(chunk)
            if not rows:
                continue
            stmt = pg_insert(KcdUCode).values(rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=["code"],
                set_={
                    "korean_name": stmt.excluded.korean_name,
                    "effective_date": stmt.excluded.effective_date,
                    "expired_date": stmt.excluded.expired_date,
                    "sex_restriction": stmt.excluded.sex_restriction,
                    "is_notifiable": stmt.excluded.is_notifiable,
                },
            )
            result = await session.execute(stmt)
            total_affected += result.rowcount
            await session.commit()

        after = (await session.execute(text("SELECT COUNT(*) FROM kcd_u_codes"))).scalar()

    await engine.dispose()
    print(f"기존 {before}개 → 삽입/갱신 처리 {total_affected}건 → 전체 {after}개")


if __name__ == "__main__":
    asyncio.run(seed())
