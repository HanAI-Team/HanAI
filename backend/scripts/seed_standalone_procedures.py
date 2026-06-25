"""
분구침술 13개 단독행위코드 시드 스크립트

실행: uv run python scripts/seed_standalone_procedures.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.database import AsyncSessionLocal
from app.core.models import FeeMaster

STANDALONE_PROCEDURES = [
    ("40121", "이침술", "분구침술"),
    ("40122", "두침술", "분구침술"),
    ("40123", "족침술", "분구침술"),
    ("40124", "수침술", "분구침술"),
    ("40125", "수지침술", "분구침술"),
    ("40126", "면침술", "분구침술"),
    ("40127", "비침술", "분구침술"),
    ("40128", "완과침술", "분구침술"),
    ("40129", "분구침술 기타(가)", "분구침술"),
    ("40131", "피내침술", "분구침술"),
    ("40132", "피부침술", "분구침술"),
    ("40133", "자석침술", "분구침술"),
    ("40134", "분구침술 기타(나)", "분구침술"),
]


async def seed():
    async with AsyncSessionLocal() as session:
        stmt = pg_insert(FeeMaster).values([
            {
                "code": code,
                "name": name,
                "category": category,
                "unit_price": 0,
                "insured_health": True,
                "insured_medical_aid": True,
                "insured_veterans": False,
                "is_standalone": True,
            }
            for code, name, category in STANDALONE_PROCEDURES
        ])
        stmt = stmt.on_conflict_do_update(
            index_elements=["code"],
            set_={"is_standalone": True},
        )
        await session.execute(stmt)
        await session.commit()
        print(f"✓ 분구침술 단독행위코드 {len(STANDALONE_PROCEDURES)}개 시드 완료")


if __name__ == "__main__":
    asyncio.run(seed())
