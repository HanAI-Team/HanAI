"""
한의맥 DB 구조 탐색 스크립트
==============================
사전 설치: pip install pyodbc

실행 방법 (한의맥서버 또는 코디서버 Windows 컴에서):
  python hanimac_inspect.py

결과를 캡처하거나 복사해서 공유해주세요.
"""

import sys

SERVER = "192.168.62.54"

CONN_STR = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={SERVER};"
    f"Trusted_Connection=yes;"
)

# ODBC Driver 17이 없으면 13으로 시도
CONN_STR_FALLBACK = (
    f"DRIVER={{ODBC Driver 13 for SQL Server}};"
    f"SERVER={SERVER};"
    f"Trusted_Connection=yes;"
)

PATIENT_KEYWORDS = ["cust", "patient", "chart", "환자", "고객", "member"]


def connect():
    try:
        import pyodbc
    except ImportError:
        print("✗ pyodbc 미설치: pip install pyodbc")
        sys.exit(1)

    for cs in [CONN_STR, CONN_STR_FALLBACK]:
        try:
            conn = pyodbc.connect(cs, timeout=5)
            print(f"✓ SQL Server 연결 성공: {SERVER}\n")
            return conn
        except Exception as e:
            print(f"  연결 시도 실패: {e}")

    print("✗ 연결 실패 — 서버 IP와 Windows 계정 권한을 확인해주세요.")
    sys.exit(1)


def list_databases(conn):
    cur = conn.cursor()
    cur.execute("SELECT name FROM sys.databases WHERE name NOT IN ('master','tempdb','model','msdb') ORDER BY name")
    dbs = [row[0] for row in cur.fetchall()]
    print("=" * 50)
    print("  데이터베이스 목록")
    print("=" * 50)
    for db in dbs:
        print(f"  - {db}")
    return dbs


def inspect_database(conn, db_name):
    cur = conn.cursor()
    try:
        cur.execute(f"USE [{db_name}]")
    except Exception as e:
        print(f"\n  [{db_name}] 접근 불가: {e}")
        return

    cur.execute("""
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_NAME
    """)
    tables = [row[0] for row in cur.fetchall()]

    patient_tables = [t for t in tables if any(k in t.lower() for k in PATIENT_KEYWORDS)]

    print(f"\n{'=' * 50}")
    print(f"  [{db_name}] — 전체 테이블 {len(tables)}개")
    print(f"{'=' * 50}")
    print(f"  전체 테이블: {', '.join(tables[:30])}{'...' if len(tables) > 30 else ''}")

    if patient_tables:
        print(f"\n  ★ 환자 관련 테이블 후보: {', '.join(patient_tables)}")
        for table in patient_tables[:5]:
            inspect_table(cur, db_name, table)
    else:
        print("\n  환자 관련 테이블 자동 감지 실패 — 전체 테이블 목록 확인 후 직접 지정하세요.")


def inspect_table(cur, db_name, table_name):
    print(f"\n  ── [{table_name}] 컬럼 구조 ──")
    try:
        cur.execute(f"""
            SELECT COLUMN_NAME, DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = '{table_name}'
            ORDER BY ORDINAL_POSITION
        """)
        cols = cur.fetchall()
        for col, dtype in cols:
            print(f"    {col} ({dtype})")

        cur.execute(f"SELECT TOP 2 * FROM [{db_name}].[dbo].[{table_name}]")
        rows = cur.fetchall()
        col_names = [d[0] for d in cur.description]
        print(f"\n  ── [{table_name}] 샘플 데이터 ──")
        for row in rows:
            for name, val in zip(col_names, row):
                print(f"    {name}: {str(val)[:60]}")
            print()
    except Exception as e:
        print(f"    오류: {e}")


if __name__ == "__main__":
    conn = connect()
    dbs = list_databases(conn)

    for db in dbs:
        inspect_database(conn, db)

    conn.close()
    print("\n✅ 탐색 완료 — 결과를 캡처해서 공유해주세요.")
