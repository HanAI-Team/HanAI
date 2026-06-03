"""
한의맥 → Zinmac 환자 데이터 이전 스크립트
==========================================
사전 설치: pip install pyodbc psycopg2-binary

실행 방법 (한의맥서버 또는 코디서버 Windows 컴에서):
  python hanimac_migration.py

- 한의맥 DB에 자동 접속하여 환자 테이블/컬럼을 탐색합니다.
- 이름, 생년월일, 성별, 전화번호 컬럼을 자동으로 감지합니다.
- 감지 결과를 확인 후 Zinmac DB로 이전합니다.
"""

import sys
import uuid
from datetime import date, datetime

HANIMAC_SERVER  = "192.168.62.54"
ZINMAC_DB_URL   = "postgresql://postgres.phdayetndkwhhzkbfevj:xorbstmddnjstmdgml321!@aws-1-ap-northeast-2.pooler.supabase.com:6543/postgres"

# 한의맥 DB명이 확인되면 아래에 입력 (비워두면 자동 탐색)
HANIMAC_DB_NAME = ""

# 환자 테이블 후보 키워드 (소문자 비교)
TABLE_KEYWORDS = ["cust", "patient", "chart", "환자", "고객", "member", "person", "client"]

# 컬럼 자동 감지 키워드
COL_NAME   = ["name", "cust_name", "이름", "성명", "환자명", "고객명", "custname", "patname"]
COL_BIRTH  = ["birth", "생년", "생일", "dob", "birthday", "birthdate", "생년월일"]
COL_GENDER = ["sex", "gender", "성별", "남여", "sexcode"]
COL_PHONE  = ["hp", "phone", "tel", "mobile", "핸드폰", "휴대폰", "전화", "연락처", "cellphone", "handphone"]
COL_ID     = ["id", "no", "code", "custid", "patid", "번호", "코드"]


# ── 연결 ────────────────────────────────────────────────────────────────────

def connect_hanimac():
    try:
        import pyodbc
    except ImportError:
        print("✗ pyodbc 미설치: pip install pyodbc")
        sys.exit(1)

    for driver in ["ODBC Driver 17 for SQL Server", "ODBC Driver 13 for SQL Server", "SQL Server"]:
        try:
            cs = f"DRIVER={{{driver}}};SERVER={HANIMAC_SERVER};Trusted_Connection=yes;"
            conn = pyodbc.connect(cs, timeout=5)
            print(f"✓ 한의맥 DB 연결 성공 (드라이버: {driver})\n")
            return conn
        except Exception:
            continue

    print("✗ SQL Server 연결 실패 — 서버 IP와 Windows 계정 권한을 확인하세요.")
    sys.exit(1)


def find_database(conn) -> str:
    if HANIMAC_DB_NAME:
        print(f"  DB: {HANIMAC_DB_NAME} (수동 지정)")
        return HANIMAC_DB_NAME

    cur = conn.cursor()
    cur.execute("SELECT name FROM sys.databases WHERE name NOT IN ('master','tempdb','model','msdb') ORDER BY name")
    dbs = [r[0] for r in cur.fetchall()]
    print(f"  발견된 DB 목록: {dbs}")

    # 한의맥 관련 키워드로 우선 후보 선정
    for db in dbs:
        if any(k in db.lower() for k in ["hani", "한의", "mac", "맥", "clinic", "한방"]):
            print(f"  → 한의맥 DB 후보 선택: {db}")
            return db

    # 후보 없으면 첫 번째 사용자 DB 사용
    if dbs:
        print(f"  → 자동 선택: {dbs[0]} (키워드 미감지, 첫 번째 DB)")
        return dbs[0]

    print("✗ 사용 가능한 DB 없음")
    sys.exit(1)


# ── 테이블/컬럼 자동 감지 ─────────────────────────────────────────────────

def find_patient_table(conn, db_name: str) -> str:
    cur = conn.cursor()
    cur.execute(f"USE [{db_name}]")
    cur.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE' ORDER BY TABLE_NAME")
    tables = [r[0] for r in cur.fetchall()]
    print(f"\n  전체 테이블 수: {len(tables)}")

    for table in tables:
        if any(k in table.lower() for k in TABLE_KEYWORDS):
            print(f"  → 환자 테이블 감지: {table}")
            return table

    print(f"  전체 테이블 목록: {tables}")
    print("✗ 환자 테이블 자동 감지 실패 — HANIMAC_DB_NAME 또는 테이블명을 직접 지정하세요.")
    sys.exit(1)


def find_columns(conn, db_name: str, table_name: str) -> dict:
    cur = conn.cursor()
    cur.execute(f"""
        SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = '{table_name}' ORDER BY ORDINAL_POSITION
    """)
    cols = [r[0] for r in cur.fetchall()]
    print(f"\n  [{table_name}] 컬럼 목록: {cols}")

    def match(keywords):
        for col in cols:
            if any(k in col.lower() for k in keywords):
                return col
        return None

    mapping = {
        "id":     match(COL_ID),
        "name":   match(COL_NAME),
        "birth":  match(COL_BIRTH),
        "gender": match(COL_GENDER),
        "phone":  match(COL_PHONE),
    }

    print(f"\n  컬럼 자동 감지 결과:")
    for field, col in mapping.items():
        status = f"✓ {col}" if col else "✗ 미감지"
        print(f"    {field:8} → {status}")

    if not mapping["name"]:
        print("\n✗ 이름 컬럼을 찾지 못했습니다. 스크립트 상단 COL_NAME 목록에 실제 컬럼명을 추가하세요.")
        sys.exit(1)

    return mapping


# ── 데이터 파싱 유틸 ─────────────────────────────────────────────────────

def parse_birth(value) -> date | None:
    s = str(value or "").strip().replace("-", "").replace("/", "")
    if len(s) >= 8:
        try:
            return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
        except Exception:
            pass
    if len(s) == 6:
        try:
            yy, mm, dd = int(s[0:2]), int(s[2:4]), int(s[4:6])
            yyyy = 2000 + yy if yy <= 24 else 1900 + yy
            return date(yyyy, mm, dd)
        except Exception:
            pass
    return None


def parse_gender(value) -> str | None:
    v = str(value or "").strip().upper()
    if v in ("M", "1", "남", "남자"):
        return "male"
    if v in ("F", "2", "여", "여자"):
        return "female"
    return None


# ── 마이그레이션 ─────────────────────────────────────────────────────────

def migrate(conn, db_name: str, table_name: str, col_map: dict):
    from sqlalchemy import create_engine, text

    cur = conn.cursor()
    cols_to_select = ", ".join(f"[{c}]" for c in col_map.values() if c)
    cur.execute(f"SELECT {cols_to_select} FROM [{db_name}].[dbo].[{table_name}]")
    col_names = [d[0] for d in cur.description]
    rows = cur.fetchall()
    print(f"\n  총 {len(rows):,}명 이전 시작...")

    # 현재 의사의 hospital_id를 DB에서 조회
    engine = create_engine(ZINMAC_DB_URL)
    with engine.connect() as zconn:
        result = zconn.execute(text("SELECT id, hospital_id FROM doctors WHERE is_approved = TRUE LIMIT 1"))
        row = result.fetchone()
        if not row:
            print("✗ Zinmac에 승인된 의사 계정이 없습니다. 먼저 로그인하여 계정을 생성하세요.")
            sys.exit(1)
        hospital_id = str(row[1])
        print(f"  hospital_id: {hospital_id}")

    def get_val(row, col_name):
        if col_name and col_name in col_names:
            return row[col_names.index(col_name)]
        return None

    now = datetime.utcnow()
    inserted = skipped = 0

    with engine.connect() as zconn:
        for row in rows:
            name = str(get_val(row, col_map["name"]) or "").strip()
            if not name:
                skipped += 1
                continue

            birth = parse_birth(get_val(row, col_map["birth"]))
            gender = parse_gender(get_val(row, col_map["gender"]))
            phone_raw = get_val(row, col_map["phone"])
            phone = str(phone_raw or "").strip() or None

            try:
                zconn.execute(text("""
                    INSERT INTO patients (id, hospital_id, name, birth_date, gender, phone, created_at)
                    VALUES (:id, :hospital_id, :name, :birth_date, :gender, :phone, :created_at)
                    ON CONFLICT DO NOTHING
                """), {
                    "id": str(uuid.uuid4()),
                    "hospital_id": hospital_id,
                    "name": name,
                    "birth_date": birth,
                    "gender": gender,
                    "phone": phone,
                    "created_at": now,
                })
                inserted += 1
            except Exception as e:
                skipped += 1
                if skipped <= 3:
                    print(f"  [오류] {e}")

        zconn.commit()

    print(f"\n✅ 완료: {inserted:,}명 이전, {skipped}건 스킵")


# ── 실행 ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  한의맥 → Zinmac 환자 데이터 이전")
    print("=" * 55)

    conn     = connect_hanimac()
    db_name  = find_database(conn)
    table    = find_patient_table(conn, db_name)
    col_map  = find_columns(conn, db_name, table)

    print("\n위 감지 결과로 이전을 진행합니다. 계속하려면 Enter, 취소하려면 Ctrl+C ...")
    input()

    migrate(conn, db_name, table, col_map)
    conn.close()
