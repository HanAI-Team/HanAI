"""마스터파일 TEXT/Excel(CSV) 추출 공통 유틸."""
import csv
import io

from fastapi import Response


def csv_response(filename: str, header: list[str], rows: list[list]) -> Response:
    buf = io.StringIO()
    buf.write("﻿")  # UTF-8 BOM — 엑셀에서 한글 깨짐 방지
    writer = csv.writer(buf)
    writer.writerow(header)
    writer.writerows(rows)
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Cache-Control": "no-store",
        },
    )
