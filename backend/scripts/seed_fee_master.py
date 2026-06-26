"""
fee_master 시딩 — catalog.py의 BILLABLE_CATALOG 기준

실행: uv run python scripts/seed_fee_master.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.billing.catalog import BILLABLE_CATALOG
from app.core.database import AsyncSessionLocal
from app.core.models import FeeMaster

STANDALONE_CODES = {
    "40121", "40122", "40123", "40124", "40125",
    "40126", "40127", "40128", "40129", "40131",
    "40132", "40133", "40134",
}


async def seed():
    rows = [
        {
            "code": item.code,
            "name": item.name,
            "category": item.category,
            "unit_price": int(item.unit_price),
            "is_insured": item.is_insured,
            "insured_health": item.is_insured,
            "insured_medical_aid": item.is_insured,
            "insured_veterans": False,
            "is_standalone": item.code in STANDALONE_CODES,
        }
        for item in BILLABLE_CATALOG
    ]

    async with AsyncSessionLocal() as session:
        stmt = pg_insert(FeeMaster).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["code"],
            set_={
                "name": stmt.excluded.name,
                "category": stmt.excluded.category,
                "unit_price": stmt.excluded.unit_price,
                "is_insured": stmt.excluded.is_insured,
            },
        )
        await session.execute(stmt)
        await session.commit()
        print(f"✓ fee_master {len(rows)}개 시드 완료")


if __name__ == "__main__":
    asyncio.run(seed())
