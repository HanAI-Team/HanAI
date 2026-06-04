"""
네오보감(BogamDB) → Zinmac 데이터 이전 스크립트 v4
===================================================
확인된 DB 구조 (실제 컬럼명 기반):
  CustMast  → patients
  DigMast   → medical_records (진료 날짜/담당의)
  DigNote   → medical_records.chart_structured (차트 텍스트 →)
  ProgressNote → medical_records.chart_structured 보조
  Hospital  → hospitals

사전 설치:
  pip install pyodbc sqlalchemy psycopg2-binary pandas

사용법:
  python neobogam_migration.py --step inspect   # 구조+샘플 확인
  python neobogam_migration.py --step extract   # CSV 추출
  python neobogam_migration.py --step migrate   # Zinmac 이전
"""

import argparse
import os
import sys
import uuid
import pandas as pd
from datetime import datetime, date

# ── 설정 ────────────────────────────────────────────────────────────────────

BOGAM_CONN = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost\\SQLEXPRESS;"
    "DATABASE=BogamDB;"
    "Trusted_Connection=yes;"
)
OUTPUT_DIR        = "./neobogam_export"
ZINMAC_DB_URL     = os.getenv("DATABASE_URL", "postgresql+psycopg2://user:password@localhost:5432/zinmac")
DEFAULT_DOCTOR_ID = os.getenv("DEFAULT_DOCTOR_ID", "")


# ── Step 1: 구조 확인 ────────────────────────────────────────────────────────

def inspect():
    print("\n" + "="*60)
    print("  네오보감 BogamDB 구조 + 샘플 확인")
    print("="*60)

    conn = _bogam_connect()
    cursor = conn.cursor()

    checks = {
        "CustMast":    "SELECT TOP 2 cm_CustID, cm_CustName, cm_Birth, cm_Sex, cm_HP FROM CustMast",
        "DigMast":     "SELECT TOP 2 dm_DiagID, dm_CustID, dm_DiagDate, dm_DiagTime FROM DigMast",
        "DigNote":     "SELECT TOP 2 dn_CustID, dn_Date, CAST(LEFT(CAST(dn_Note AS nvarchar(300)),300) AS nvarchar(300)) FROM DigNote WHERE DATALENGTH(dn_Note)>0",
        "ProgressNote":"SELECT TOP 2 pn_CustID, pn_MemoDate, LEFT(pn_Memo,200) FROM ProgressNote WHERE DATALENGTH(pn_Memo)>0",
        "Hospital":    "SELECT TOP 1 hsp_Name, hsp_Tel, hsp_Addr FROM Hospital",
    }

    for table, query in checks.items():
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            cursor.execute(query)
            cols = [d[0] for d in cursor.description]
            rows = cursor.fetchall()
            print(f"\n  [{table}] {count:,}행")
            for row in rows:
                for col, val in zip(cols, row):
                    print(f"    {col}: {str(val)[:80]}")
        except Exception as e:
            print(f"\n  [{table}] 오류: {e}")

    conn.close()


# ── Step 2: CSV 추출 ─────────────────────────────────────────────────────────

def extract():
    print("\n" + "="*60)
    print("  BogamDB → CSV 추출")
    print("="*60)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    conn = _bogam_connect()

    queries = {
        "CustMast":     "SELECT cm_CustID, cm_ChartID, cm_CustName, cm_LifeNo, cm_Sex, cm_Birth, cm_HP, cm_Tel, cm_FirstDate, cm_LastDate FROM CustMast",
        "DigMast":      "SELECT dm_DiagID, dm_CustID, dm_DiagDate, dm_DiagTime, dm_DrEmp FROM DigMast",
        "DigNote":      "SELECT dn_CustID, dn_Date, CAST(dn_Note AS nvarchar(max)) as dn_Note, dn_SaveDay FROM DigNote",
        "ProgressNote": "SELECT pn_CustID, pn_MemoDate, pn_MemoTime, pn_Memo, pn_Doctor FROM ProgressNote",
        "Hospital":     "SELECT hsp_Code, hsp_Name, hsp_Tel, hsp_Addr FROM Hospital",
        "DigHerbPrs":   "SELECT * FROM DigHerbPrs",
        "DigAcupoint":  "SELECT * FROM DigAcupoint",
    }

    for name, query in queries.items():
        try:
            df = pd.read_sql(query, conn)
            path = os.path.join(OUTPUT_DIR, f"{name}.csv")
            df.to_csv(path, index=False, encoding="utf-8-sig")
            print(f"  ✓ {name:<20} {len(df):>8,}행  →  {path}")
        except Exception as e:
            print(f"  ✗ {name}: {e}")

    conn.close()
    print(f"\n✅ 추출 완료 → {OUTPUT_DIR}/")


# ── Step 3: Zinmac 이전 ──────────────────────────────────────────────────────

def migrate():
    print("\n" + "="*60)
    print("  Zinmac DB 이전 시작")
    print("="*60)

    if not DEFAULT_DOCTOR_ID:
        print("✗ DEFAULT_DOCTOR_ID 환경변수 필요:")
        print("   set DEFAULT_DOCTOR_ID=<Zinmac 의사 UUID>")
        sys.exit(1)

    from sqlalchemy import create_engine
    engine   = create_engine(ZINMAC_DB_URL)
    bogam    = _bogam_connect()

    hospital_id = _migrate_hospital(engine, bogam)
    patient_map = _migrate_patients(engine, bogam, hospital_id)
    chart_map   = _build_chart_map(bogam)
    record_map  = _migrate_records(engine, bogam, patient_map, hospital_id, chart_map)
    _migrate_prescriptions(engine, bogam, record_map)

    bogam.close()
    print("\n✅ 전체 이전 완료!")


# ── 이전 함수들 ──────────────────────────────────────────────────────────────

def _migrate_hospital(engine, bogam) -> str:
    from sqlalchemy import text
    cursor = bogam.cursor()
    cursor.execute("SELECT TOP 1 hsp_Name, hsp_Tel, hsp_Addr FROM Hospital")
    row = cursor.fetchone()
    name = str(row[0] or "").strip() if row else "네오보감한의원"
    tel  = str(row[1] or "").strip() if row else ""
    addr = str(row[2] or "").strip() if row else ""

    hospital_id = str(uuid.uuid4())
    now = datetime.utcnow()
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO hospitals (id, name, phone, address, created_at)
            VALUES (:id, :name, :phone, :address, :created_at)
            ON CONFLICT DO NOTHING
        """), {"id": hospital_id, "name": name, "phone": tel,
               "address": addr, "created_at": now})
        conn.commit()

    print(f"\n🏥 병원: {name}  (id: {hospital_id})")
    return hospital_id


def _migrate_patients(engine, bogam, hospital_id: str) -> dict:
    from sqlalchemy import text
    cursor = bogam.cursor()
    cursor.execute("""
        SELECT cm_CustID, cm_CustName, cm_LifeNo, cm_Sex, cm_Birth, cm_HP, cm_Tel
        FROM CustMast
        WHERE cm_CustName IS NOT NULL AND LEN(LTRIM(RTRIM(cm_CustName))) > 0
    """)
    rows = cursor.fetchall()
    print(f"\n👤 환자 이전: {len(rows):,}명")

    now = datetime.utcnow()
    id_map = {}
    inserted = skipped = 0

    with engine.connect() as conn:
        for row in rows:
            try:
                cm_id, name, life_no, sex, birth, hp, tel = row
                new_id     = str(uuid.uuid4())
                birth_date = _parse_yyyymmdd(birth) or _birth_from_lifeno(life_no)
                gender     = _normalize_gender(sex)
                phone      = str(hp or tel or "").strip() or None

                conn.execute(text("""
                    INSERT INTO patients
                        (id, hospital_id, name, birth_date, gender, phone, created_at)
                    VALUES
                        (:id, :hospital_id, :name, :birth_date, :gender, :phone, :created_at)
                    ON CONFLICT DO NOTHING
                """), {
                    "id": new_id, "hospital_id": hospital_id,
                    "name": name.strip(), "birth_date": birth_date,
                    "gender": gender, "phone": phone, "created_at": now,
                })
                id_map[cm_id] = new_id
                inserted += 1
            except Exception as e:
                skipped += 1
                if skipped <= 3:
                    print(f"  [오류] {e}")
        conn.commit()

    print(f"  ✓ {inserted:,}명 이전, {skipped}건 스킵")
    return id_map


def _build_chart_map(bogam) -> dict:
    """DigNote 전체를 메모리에 로드 → {cm_CustID: {yyyymmdd: note_text}}"""
    print("\n📋 차트 텍스트 로딩 중...")
    cursor = bogam.cursor()

    chart_map = {}

    try:
        cursor.execute("""
            SELECT dn_CustID, dn_Date,
                   CAST(dn_Note AS nvarchar(max)) as note
            FROM DigNote
            WHERE DATALENGTH(dn_Note) > 0
        """)
        for row in cursor.fetchall():
            cust_id, dt, note = row
            if cust_id not in chart_map:
                chart_map[cust_id] = {}
            date_key = str(dt or "").strip()[:8]
            chart_map[cust_id][date_key] = str(note or "").strip()
        print(f"  DigNote: {sum(len(v) for v in chart_map.values()):,}건 로드")
    except Exception as e:
        print(f"  DigNote 로드 오류: {e}")

    try:
        cursor.execute("""
            SELECT pn_CustID, pn_MemoDate, pn_Memo
            FROM ProgressNote
            WHERE DATALENGTH(pn_Memo) > 0
        """)
        pn_count = 0
        for row in cursor.fetchall():
            cust_id, dt, memo = row
            if not cust_id or not memo:
                continue
            date_key = str(dt or "").strip()[:8]
            memo_str = str(memo or "").strip()
            if cust_id not in chart_map:
                chart_map[cust_id] = {}
            if date_key in chart_map[cust_id]:
                chart_map[cust_id][date_key] += f"\n[경과] {memo_str}"
            else:
                chart_map[cust_id][date_key] = f"[경과] {memo_str}"
            pn_count += 1
        print(f"  ProgressNote: {pn_count:,}건 로드")
    except Exception as e:
        print(f"  ProgressNote 로드 오류: {e}")

    print(f"  총 {len(chart_map):,}명 차트 데이터 준비 완료")
    return chart_map


def _migrate_records(engine, bogam, patient_map: dict,
                     hospital_id: str, chart_map: dict) -> dict:
    from sqlalchemy import text
    cursor = bogam.cursor()
    cursor.execute("""
        SELECT dm_DiagID, dm_CustID, dm_DiagDate, dm_DiagTime, dm_DrEmp
        FROM DigMast
        WHERE dm_CustID IS NOT NULL
    """)
    rows = cursor.fetchall()
    print(f"\n📁 진료기록 이전: {len(rows):,}건")

    now = datetime.utcnow()
    id_map = {}
    inserted = skipped = chart_matched = 0

    with engine.connect() as conn:
        for row in rows:
            try:
                diag_id, cust_id, diag_date, diag_time, dr_emp = row
                patient_id = patient_map.get(cust_id)
                if not patient_id:
                    skipped += 1
                    continue

                new_id      = str(uuid.uuid4())
                recorded_at = _parse_diagdatetime(diag_date, diag_time)
                date_key    = str(diag_date or "").strip()[:8]
                chart_text  = chart_map.get(cust_id, {}).get(date_key)
                if chart_text:
                    chart_matched += 1

                conn.execute(text("""
                    INSERT INTO medical_records
                        (id, patient_id, doctor_id, hospital_id,
                         chart_structured, status, recorded_at, created_at)
                    VALUES
                        (:id, :patient_id, :doctor_id, :hospital_id,
                         :chart_structured, 'completed', :recorded_at, :created_at)
                    ON CONFLICT DO NOTHING
                """), {
                    "id":               new_id,
                    "patient_id":       patient_id,
                    "doctor_id":        DEFAULT_DOCTOR_ID,
                    "hospital_id":      hospital_id,
                    "chart_structured": chart_text,
                    "recorded_at":      recorded_at,
                    "created_at":       now,
                })
                id_map[diag_id] = new_id
                inserted += 1

            except Exception as e:
                skipped += 1
                if skipped <= 3:
                    print(f"  [오류] {e}")

        conn.commit()

    print(f"  ✓ {inserted:,}건 이전 (차트 텍스트 매칭: {chart_matched:,}건), {skipped}건 스킵")
    return id_map


def _migrate_prescriptions(engine, bogam, record_map: dict):
    from sqlalchemy import text
    cursor = bogam.cursor()

    try:
        cursor.execute("SELECT TOP 1 * FROM DigHerbPrs")
        cols = [d[0] for d in cursor.description]
    except Exception as e:
        print(f"\n⚠️  DigHerbPrs 조회 실패: {e}")
        return

    diag_col = next((c for c in cols if "DiagID" in c), None)
    name_col = next((c for c in cols if "PrsName" in c or "HerbName" in c or "Name" in c), None)
    herb_col = next((c for c in cols if "Herb" in c and c != name_col), None)

    print(f"\n💊 처방 이전 (DigHerbPrs)")
    print(f"  감지된 컬럼 → DiagID:{diag_col}, Name:{name_col}, Herb:{herb_col}")

    if not diag_col:
        print("  ⚠️  DiagID 컬럼 못 찾음 → 스킵")
        return

    select_cols = ", ".join(filter(None, [diag_col, name_col, herb_col]))
    cursor.execute(f"SELECT {select_cols} FROM DigHerbPrs")
    rows = cursor.fetchall()
    print(f"  {len(rows):,}건 처리 중...")

    now = datetime.utcnow()
    inserted = skipped = 0

    with engine.connect() as conn:
        for row in rows:
            try:
                diag_id   = row[0]
                prs_name  = str(row[1] or "").strip() if len(row) > 1 else ""
                herb_text = str(row[2] or "").strip() if len(row) > 2 else ""
                record_id = record_map.get(diag_id)
                if not record_id:
                    skipped += 1
                    continue

                conn.execute(text("""
                    INSERT INTO prescriptions
                        (id, medical_record_id, prescription_name, ingredients, created_at)
                    VALUES
                        (:id, :medical_record_id, :prescription_name, :ingredients, :created_at)
                    ON CONFLICT DO NOTHING
                """), {
                    "id":                str(uuid.uuid4()),
                    "medical_record_id": record_id,
                    "prescription_name": prs_name or None,
                    "ingredients":       herb_text or None,
                    "created_at":        now,
                })
                inserted += 1
            except Exception as e:
                skipped += 1
                if skipped <= 3:
                    print(f"  [오류] {e}")
        conn.commit()

    print(f"  ✓ {inserted:,}건 이전, {skipped}건 스킵")


# ── 유틸 ────────────────────────────────────────────────────────────────────

def _bogam_connect():
    try:
        import pyodbc
        return pyodbc.connect(BOGAM_CONN)
    except ImportError:
        print("✗ pyodbc 미설치: pip install pyodbc")
        sys.exit(1)
    except Exception as e:
        print(f"✗ BogamDB 연결 실패: {e}")
        sys.exit(1)


def _parse_yyyymmdd(value) -> date | None:
    if not value:
        return None
    s = str(value).strip().replace("-", "")
    if len(s) >= 8:
        try:
            return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
        except Exception:
            pass
    return None


def _birth_from_lifeno(life_no) -> date | None:
    """주민번호 앞 6자리 + 7번째 자리로 생년월일 추출"""
    if not life_no:
        return None
    s = str(life_no).strip().replace("-", "")
    if len(s) < 7:
        return None
    try:
        yy, mm, dd    = int(s[0:2]), int(s[2:4]), int(s[4:6])
        century_digit = int(s[6])
        yyyy = 2000 + yy if century_digit in (3, 4) else 1900 + yy
        return date(yyyy, mm, dd)
    except Exception:
        return None


def _parse_diagdatetime(diag_date, diag_time):
    try:
        d = str(diag_date or "").strip()
        t = str(diag_time or "0000").strip().zfill(4)
        if len(d) == 8:
            return datetime(int(d[:4]), int(d[4:6]), int(d[6:8]),
                            int(t[:2]), int(t[2:4]))
    except Exception:
        pass
    return None


def _normalize_gender(value) -> str | None:
    v = str(value or "").strip().upper()
    if v in ("M", "1", "남"):
        return "male"
    if v in ("F", "2", "여"):
        return "female"
    return None


# ── 엔트리포인트 ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="네오보감 → Zinmac 이전 v4")
    parser.add_argument("--step", choices=["inspect", "extract", "migrate", "all"],
                        default="inspect")
    args = parser.parse_args()

    if args.step == "inspect":
        inspect()
    elif args.step == "extract":
        extract()
    elif args.step == "migrate":
        migrate()
    elif args.step == "all":
        inspect()
        extract()
        migrate()
