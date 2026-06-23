import asyncio
import csv
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from app.core.database import AsyncSessionLocal
from sqlalchemy import text

MERIDIAN_MAP = {
    "BA": "경외기혈(배부)", "BL": "방광경", "CA": "경외기혈(흉복부)",
    "CV": "임맥", "GB": "담경", "GV": "독맥", "HN": "경외기혈(두경부)",
    "HT": "심경", "KI": "신경", "LE": "경외기혈(하지)", "LI": "대장경",
    "LR": "간경", "LU": "폐경", "PC": "심포경", "SI": "소장경",
    "SP": "비경", "ST": "위경", "TE": "삼초경", "UE": "경외기혈(상지)",
}

CSV_PATH = os.path.join(os.path.dirname(__file__), "../data/acupuncture_points.csv")


async def seed():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT COUNT(*) FROM acupuncture_points"))
        if result.scalar() > 0:
            print("이미 데이터 존재. 스킵.")
            return

        rows = []
        with open(CSV_PATH, encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  
            for code, name in reader:
                prefix = code[:2]
                rows.append({
                    "code": code.strip(),
                    "korean_name": name.strip(),
                    "meridian": MERIDIAN_MAP.get(prefix, "기타"),
                })

        await session.execute(
            text("INSERT INTO acupuncture_points (code, korean_name, meridian) VALUES (:code, :korean_name, :meridian)"),
            rows,
        )
        await session.commit()
        print(f"{len(rows)}개 혈위 시딩 완료.")


if __name__ == "__main__":
    asyncio.run(seed())