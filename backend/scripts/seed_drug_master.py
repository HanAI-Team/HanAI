"""약제급여목록 및 급여상한금액표 시딩 스크립트.

원본: 심평원 「약제급여목록 및 급여상한금액표」(2026.7.1. 공개용(인가자용)) 엑셀.
전국 공통 데이터(양·한방 구분 없음) 21,959건 전체를 적재한다 (치료재료는
한방 관련 코드가 없어 제외 — 2026-07-10 확인).

실행: cd backend && python scripts/seed_drug_master.py <엑셀_파일_경로>
"""
import asyncio
import os
import sys
from datetime import date

import pandas as pd
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.models import DrugMaster

CHUNK_SIZE = 1000
EFFECTIVE_DATE = date(2026, 7, 1)  # 파일명("2026.7.1. 적용") 기준 스냅샷 적용일

COLUMNS = [
    "seq", "route", "classification", "kfda_classification",
    "ingredient_code_same_form", "ingredient_code", "ingredient_count",
    "ingredient_name", "product_code", "product_name", "company_name",
    "spec", "unit", "unit_price", "agreed_price",
    "prescription_flag",  # 헤더는 "전일"이라 표기되어 있지만 실제 값은 전문/일반
    "note",
]


def _row_to_dict(row: pd.Series) -> dict:
    return {
        "product_code": str(row["product_code"]).strip(),
        "product_name": str(row["product_name"]).strip(),
        "ingredient_code": (str(row["ingredient_code"]).strip() or None) if pd.notna(row["ingredient_code"]) else None,
        "ingredient_name": (str(row["ingredient_name"]).strip() or None) if pd.notna(row["ingredient_name"]) else None,
        "company_name": (str(row["company_name"]).strip() or None) if pd.notna(row["company_name"]) else None,
        "spec": (str(row["spec"]).strip() or None) if pd.notna(row["spec"]) else None,
        "unit": (str(row["unit"]).strip() or None) if pd.notna(row["unit"]) else None,
        "unit_price": int(row["unit_price"]) if pd.notna(row["unit_price"]) else 0,
        "administration_route": (str(row["route"]).strip() or None) if pd.notna(row["route"]) else None,
        "classification_code": (str(row["classification"]).strip() or None) if pd.notna(row["classification"]) else None,
        "is_prescription": (str(row["prescription_flag"]).strip() == "전문") if pd.notna(row["prescription_flag"]) else None,
        "effective_date": EFFECTIVE_DATE,
    }


async def seed(xlsx_path: str) -> None:
    db_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(db_url, echo=False, connect_args={"statement_cache_size": 0})
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    df = pd.read_excel(xlsx_path, sheet_name=0, header=0, names=COLUMNS, dtype=str, engine="openpyxl")
    # unit_price는 숫자 연산이 필요해 별도로 숫자형 변환 (엑셀에서 dtype=str로 읽었으므로)
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce").fillna(0)
    df = df.drop_duplicates(subset="product_code", keep="first")

    total_affected = 0
    async with async_session() as session:
        before = (await session.execute(text("SELECT COUNT(*) FROM drug_master"))).scalar()

        for start in range(0, len(df), CHUNK_SIZE):
            chunk = df.iloc[start:start + CHUNK_SIZE]
            rows = [_row_to_dict(row) for _, row in chunk.iterrows()]
            stmt = pg_insert(DrugMaster).values(rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=["product_code"],
                set_={
                    "product_name": stmt.excluded.product_name,
                    "ingredient_code": stmt.excluded.ingredient_code,
                    "ingredient_name": stmt.excluded.ingredient_name,
                    "company_name": stmt.excluded.company_name,
                    "spec": stmt.excluded.spec,
                    "unit": stmt.excluded.unit,
                    "unit_price": stmt.excluded.unit_price,
                    "administration_route": stmt.excluded.administration_route,
                    "classification_code": stmt.excluded.classification_code,
                    "is_prescription": stmt.excluded.is_prescription,
                    "effective_date": stmt.excluded.effective_date,
                },
            )
            result = await session.execute(stmt)
            total_affected += result.rowcount
            await session.commit()

        after = (await session.execute(text("SELECT COUNT(*) FROM drug_master"))).scalar()

    await engine.dispose()
    print(f"기존 {before}개 → 삽입/갱신 처리 {total_affected}건 → 전체 {after}개")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python scripts/seed_drug_master.py <엑셀_파일_경로>")
        sys.exit(1)
    asyncio.run(seed(sys.argv[1]))
