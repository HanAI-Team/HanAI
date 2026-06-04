"""
한의맥 → Zinmac 자동 동기화 에이전트
======================================
처음 실행 시: 한의맥 전체 환자를 Zinmac으로 이전
이후 실행 시: 새로 추가된 환자만 동기화

설치: hanimac_setup.bat 실행 (Windows 작업 스케줄러 자동 등록)
수동 실행: python hanimac_sync_agent.py
"""

import json
import sys
import uuid
import requests
from datetime import date, datetime
from pathlib import Path

# ── 설정 ────────────────────────────────────────────────────────────────────

HANIMAC_SERVER  = "192.168.62.54"
ZINMAC_API_URL  = "https://hanbang.vercel.app"   # 배포 후 실제 URL로 변경
ZINMAC_LICENSE  = ""   # 처음 실행 시 입력 요청
ZINMAC_PASSWORD = ""   # 처음 실행 시 입력 요청

CONFIG_FILE = Path(__file__).parent / "sync_config.json"
STATE_FILE  = Path(__file__).parent / "sync_state.json"

TABLE_KEYWORDS = ["cust", "patient", "chart", "환자", "고객", "member"]
COL_NAME   = ["name", "cust_name", "이름", "성명", "환자명", "고객명", "custname", "patname"]
COL_BIRTH  = ["birth", "생년", "생일", "dob", "birthday", "birthdate", "생년월일"]
COL_GENDER = ["sex", "gender", "성별", "sexcode"]
COL_PHONE  = ["hp", "phone", "tel", "mobile", "핸드폰", "휴대폰", "전화", "연락처", "cellphone"]
COL_ID     = ["id", "no", "code", "custid", "patid", "번호", "코드"]


# ── 설정 파일 ────────────────────────────────────────────────────────────────

def load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    return {}


def save_config(cfg: dict):
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"synced_ids": [], "last_sync": None}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Zinmac 인증 ──────────────────────────────────────────────────────────────

def get_zinmac_token(cfg: dict) -> str:
    # 저장된 토큰이 있으면 재사용
    if cfg.get("token"):
        return cfg["token"]

    license_no = cfg.get("license_number") or input("Zinmac 면허번호: ").strip()
    password   = cfg.get("password") or input("Zinmac 비밀번호: ").strip()

    res = requests.post(f"{ZINMAC_API_URL}/api/auth/login", json={
        "license_number": license_no,
        "password": password,
    })
    if not res.ok:
        print(f"✗ Zinmac 로그인 실패: {res.text}")
        sys.exit(1)

    token = res.json()["access_token"]
    cfg["license_number"] = license_no
    cfg["password"] = password
    cfg["token"] = token
    save_config(cfg)
    print("✓ Zinmac 로그인 성공")
    return token


# ── 한의맥 DB 연결 ────────────────────────────────────────────────────────────

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
            return conn
        except Exception:
            continue

    print("✗ 한의맥 DB 연결 실패 — 한의맥서버 컴퓨터에서 실행하고 있는지 확인하세요.")
    sys.exit(1)


def detect_db(conn, cfg: dict) -> str:
    if cfg.get("db_name"):
        return cfg["db_name"]

    cur = conn.cursor()
    cur.execute("SELECT name FROM sys.databases WHERE name NOT IN ('master','tempdb','model','msdb')")
    dbs = [r[0] for r in cur.fetchall()]

    for db in dbs:
        if any(k in db.lower() for k in ["hani", "한의", "mac", "맥", "clinic"]):
            return db

    return dbs[0] if dbs else None


def detect_table(conn, db_name: str, cfg: dict) -> str:
    if cfg.get("table_name"):
        return cfg["table_name"]

    cur = conn.cursor()
    cur.execute(f"USE [{db_name}]")
    cur.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'")
    tables = [r[0] for r in cur.fetchall()]

    for t in tables:
        if any(k in t.lower() for k in TABLE_KEYWORDS):
            return t
    return None


def detect_columns(conn, db_name: str, table_name: str, cfg: dict) -> dict:
    if cfg.get("col_map"):
        return cfg["col_map"]

    cur = conn.cursor()
    cur.execute(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='{table_name}' ORDER BY ORDINAL_POSITION")
    cols = [r[0] for r in cur.fetchall()]

    def match(keywords):
        for col in cols:
            if any(k in col.lower() for k in keywords):
                return col
        return None

    return {
        "id":     match(COL_ID),
        "name":   match(COL_NAME),
        "birth":  match(COL_BIRTH),
        "gender": match(COL_GENDER),
        "phone":  match(COL_PHONE),
    }


# ── 파싱 유틸 ────────────────────────────────────────────────────────────────

def parse_birth(value) -> str | None:
    s = str(value or "").strip().replace("-", "").replace("/", "")
    try:
        if len(s) >= 8:
            d = date(int(s[:4]), int(s[4:6]), int(s[6:8]))
            return d.isoformat()
        if len(s) == 6:
            yy, mm, dd = int(s[0:2]), int(s[2:4]), int(s[4:6])
            yyyy = 2000 + yy if yy <= 24 else 1900 + yy
            return date(yyyy, mm, dd).isoformat()
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


# ── 동기화 ───────────────────────────────────────────────────────────────────

def sync(conn, db_name: str, table_name: str, col_map: dict, token: str, state: dict):
    cur = conn.cursor()
    synced_ids = set(state.get("synced_ids", []))

    id_col   = col_map.get("id")
    name_col = col_map.get("name")
    cols_to_select = ", ".join(f"[{c}]" for c in col_map.values() if c)

    cur.execute(f"SELECT {cols_to_select} FROM [{db_name}].[dbo].[{table_name}]")
    col_names = [d[0] for d in cur.description]
    rows = cur.fetchall()

    def get_val(row, col):
        if col and col in col_names:
            return row[col_names.index(col)]
        return None

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    inserted = skipped = errors = 0

    for row in rows:
        row_id = str(get_val(row, id_col) or "")
        if row_id in synced_ids:
            skipped += 1
            continue

        name = str(get_val(row, name_col) or "").strip()
        if not name:
            skipped += 1
            continue

        payload = {
            "name": name,
            "birth_date": parse_birth(get_val(row, col_map.get("birth"))),
            "gender":     parse_gender(get_val(row, col_map.get("gender"))),
            "phone":      str(get_val(row, col_map.get("phone")) or "").strip() or None,
        }

        res = requests.post(f"{ZINMAC_API_URL}/api/patients/register", json=payload, headers=headers)

        if res.ok:
            inserted += 1
            if row_id:
                synced_ids.add(row_id)
        elif res.status_code == 401:
            # 토큰 만료 — 재로그인 필요
            print("✗ 토큰 만료 — sync_config.json에서 token 항목을 삭제 후 재실행하세요.")
            break
        else:
            errors += 1

    state["synced_ids"] = list(synced_ids)
    state["last_sync"] = datetime.now().isoformat()
    save_state(state)

    print(f"✅ 동기화 완료: {inserted}명 신규 등록, {skipped}명 스킵, {errors}건 오류")
    print(f"   마지막 동기화: {state['last_sync']}")


# ── 실행 ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] 한의맥 동기화 시작")

    cfg   = load_config()
    state = load_state()

    # Zinmac 인증
    token = get_zinmac_token(cfg)

    # 한의맥 DB 연결 및 구조 탐색
    conn = connect_hanimac()

    db_name = detect_db(conn, cfg)
    if not db_name:
        print("✗ 한의맥 DB를 찾을 수 없습니다.")
        sys.exit(1)

    table = detect_table(conn, db_name, cfg)
    if not table:
        print("✗ 환자 테이블을 찾을 수 없습니다.")
        sys.exit(1)

    col_map = detect_columns(conn, db_name, table, cfg)

    # 감지 결과 저장 (다음 실행부터 재탐색 없이 사용)
    cfg["db_name"]    = db_name
    cfg["table_name"] = table
    cfg["col_map"]    = col_map
    save_config(cfg)

    is_first = not state.get("last_sync")
    if is_first:
        count_cur = conn.cursor()
        count_cur.execute(f"SELECT COUNT(*) FROM [{db_name}].[dbo].[{table}]")
        total = count_cur.fetchone()[0]
        print(f"\n첫 실행 — 전체 {total:,}명 이전합니다.")

    sync(conn, db_name, table, col_map, token, state)
    conn.close()
