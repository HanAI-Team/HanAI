"""
네오보감 → Zinmac 자동 동기화 에이전트
========================================
처음 실행 시: 네오보감 전체 환자를 Zinmac으로 이전
이후 실행 시: 새로 추가된 환자만 동기화

설치: neobogam_setup.bat 실행 (Windows 작업 스케줄러 자동 등록)
수동 실행: python neobogam_sync_agent.py
"""

import json
import sys
import requests
from datetime import date, datetime
from pathlib import Path

# ── 설정 ────────────────────────────────────────────────────────────────────

BOGAM_SERVER    = "localhost\\SQLEXPRESS"
BOGAM_DB        = "BogamDB"
ZINMAC_API_URL  = "https://hanbang.vercel.app"   # 배포 후 실제 URL로 변경

CONFIG_FILE = Path(__file__).parent / "neobogam_sync_config.json"
STATE_FILE  = Path(__file__).parent / "neobogam_sync_state.json"

BOGAM_CONN = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={BOGAM_SERVER};"
    f"DATABASE={BOGAM_DB};"
    f"Trusted_Connection=yes;"
)
BOGAM_CONN_FALLBACK = BOGAM_CONN.replace("ODBC Driver 17", "ODBC Driver 13")


# ── 설정/상태 파일 ───────────────────────────────────────────────────────────

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


# ── 네오보감 연결 ────────────────────────────────────────────────────────────

def connect_bogam():
    try:
        import pyodbc
    except ImportError:
        print("✗ pyodbc 미설치: pip install pyodbc")
        sys.exit(1)

    for cs in [BOGAM_CONN, BOGAM_CONN_FALLBACK]:
        try:
            return pyodbc.connect(cs, timeout=5)
        except Exception:
            continue

    print("✗ 네오보감 DB 연결 실패 — 네오보감이 설치된 컴퓨터에서 실행하세요.")
    sys.exit(1)


# ── 파싱 유틸 ────────────────────────────────────────────────────────────────

def parse_birth(value) -> str | None:
    s = str(value or "").strip().replace("-", "")
    try:
        if len(s) >= 8:
            return date(int(s[:4]), int(s[4:6]), int(s[6:8])).isoformat()
    except Exception:
        pass
    # 주민번호 앞자리로 추출
    if len(s) >= 7:
        try:
            yy, mm, dd = int(s[0:2]), int(s[2:4]), int(s[4:6])
            yyyy = 2000 + yy if int(s[6]) in (3, 4) else 1900 + yy
            return date(yyyy, mm, dd).isoformat()
        except Exception:
            pass
    return None


def parse_gender(value) -> str | None:
    v = str(value or "").strip().upper()
    if v in ("M", "1", "남"):
        return "male"
    if v in ("F", "2", "여"):
        return "female"
    return None


# ── 동기화 ───────────────────────────────────────────────────────────────────

def sync(conn, token: str, state: dict):
    cur = conn.cursor()
    cur.execute("""
        SELECT cm_CustID, cm_CustName, cm_LifeNo, cm_Sex, cm_Birth, cm_HP, cm_Tel
        FROM CustMast
        WHERE cm_CustName IS NOT NULL AND LEN(LTRIM(RTRIM(cm_CustName))) > 0
    """)
    rows = cur.fetchall()

    synced_ids = set(str(s) for s in state.get("synced_ids", []))
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    inserted = skipped = errors = 0

    for cm_id, name, life_no, sex, birth, hp, tel in rows:
        row_id = str(cm_id or "")
        if row_id in synced_ids:
            skipped += 1
            continue

        name = str(name or "").strip()
        if not name:
            skipped += 1
            continue

        birth_str = parse_birth(birth) or parse_birth(life_no)
        phone = str(hp or tel or "").strip() or None

        payload = {
            "name":       name,
            "birth_date": birth_str,
            "gender":     parse_gender(sex),
            "phone":      phone,
        }

        res = requests.post(f"{ZINMAC_API_URL}/api/patients/register", json=payload, headers=headers)

        if res.ok:
            inserted += 1
            if row_id:
                synced_ids.add(row_id)
        elif res.status_code == 401:
            print("✗ 토큰 만료 — neobogam_sync_config.json에서 token 항목을 삭제 후 재실행하세요.")
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
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] 네오보감 동기화 시작")

    cfg   = load_config()
    state = load_state()

    token = get_zinmac_token(cfg)
    conn  = connect_bogam()

    if not state.get("last_sync"):
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM CustMast")
        total = cur.fetchone()[0]
        print(f"첫 실행 — 전체 {total:,}명 이전합니다.")

    sync(conn, token, state)
    conn.close()
