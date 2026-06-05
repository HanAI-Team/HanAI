"""
RAG 데이터셋 빌더
=================
출력:
  rag_prescriptions.jsonl  — 한의학 처방/약재 구조화 지식
  rag_clinical.jsonl       — 카페 임상 토론 데이터
"""

import json
import re
import pandas as pd
from pathlib import Path

BASE = Path(__file__).parent
OUT_PRESCRIPTIONS = BASE / "rag_prescriptions.jsonl"
OUT_CLINICAL      = BASE / "rag_clinical.jsonl"

# ── 1. 한의학 내과학 처방 데이터 ─────────────────────────────────────────────

NAEGWA_FILES = [
    "간계내과학.csv",
    "비계내과학.csv",
    "신계내과학.csv",
    "심계내과학.csv",
    "폐계내과학.csv",
]

def build_prescriptions():
    dfs = []
    for fname in NAEGWA_FILES:
        path = BASE / fname
        if not path.exists():
            print(f"  [건너뜀] {fname}")
            continue
        df = pd.read_csv(path, encoding="utf-8-sig", dtype=str).fillna("")
        df["_계"] = fname.replace("내과학.csv", "")
        dfs.append(df)

    df = pd.concat(dfs, ignore_index=True)
    print(f"내과학 원본: {len(df):,}행")

    records = []
    # 처방 단위로 묶기
    grouped = df.groupby(["처방아이디", "처방한글명", "처방한자명"])

    for (pid, name_kr, name_cn), group in grouped:
        if not name_kr.strip():
            continue

        row0 = group.iloc[0]
        증상 = row0["증상한글명"].strip()
        설명 = row0["일반인설명"].strip()
        출전 = row0["출전"].strip()
        계  = row0["_계"]

        # 약재 목록
        herbs = []
        for _, r in group.iterrows():
            herb = r["약재한글명"].strip()
            if not herb:
                continue
            parts = []
            if r["귀경"]:  parts.append(f"귀경:{r['귀경']}")
            if r["성"]:    parts.append(f"성:{r['성']}")
            if r["미"]:    parts.append(f"미:{r['미']}")
            if r["용량"] and r["단위"]: parts.append(f"{r['용량']}{r['단위']}")
            herbs.append(f"{herb}({', '.join(parts)})" if parts else herb)

        text = f"[처방] {name_kr}"
        if name_cn: text += f" ({name_cn})"
        if 계:      text += f" / {계}"
        if 출전:    text += f"\n[출전] {출전}"
        if 증상:    text += f"\n[주치] {증상}"
        if 설명:    text += f"\n[설명] {설명}"
        if herbs:   text += f"\n[약재] {', '.join(herbs)}"

        records.append({
            "id":      pid,
            "type":    "prescription",
            "계":      계,
            "처방명":  name_kr,
            "증상":    증상,
            "text":    text,
        })

    with open(OUT_PRESCRIPTIONS, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"처방 데이터: {len(records):,}건 → {OUT_PRESCRIPTIONS.name}")
    return len(records)


# ── 2. 카페 임상 데이터 ──────────────────────────────────────────────────────

CLINICAL_FILES = {
    "cafe_acupuncture_data.csv": "침구",
    "cafe_diagnosis_data.csv":   "진단",
    "cafe_침처방_data.csv":      "침처방",
    "cafe_주소증_data.csv":      "주소증",
    "cafe_구안와사_data.csv":    "구안와사",
    "cafe_안면마비_data.csv":    "안면마비",
    "cafe_람세이헌트_data.csv":  "람세이헌트",
}

BOILERPLATE = re.compile(
    r"%양의사[^\n]*|"
    r"%성분명처방[^\n]*|"
    r"<link\s[^>]*>|<script[^>]*>.*?</script>|<style[^>]*>.*?</style>|<[^>]+>|"
    r"\[보안코디[^\]]*\][^\n]*\n?|"
    r"\[원글자에게 저작권이[^\]]*\][^\n]*\n?|"
    r"복사금지 스크랩금지[^\n]*\n?|"
    r"이 글을 보[기려].*?로그인[^\n]*\n?|"
    r"보안필드에 적[^\n]*\n?|"
    r"게시글 본문내용|이 게시글은 클린봇에|신고 사유|첨부파일|\.pdf[\d\.KB]+",
    re.IGNORECASE | re.DOTALL
)

def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = text.replace("\xa0", " ")
    text = BOILERPLATE.sub("", text)
    # daum cafe URL 축약 (너무 길면 노이즈)
    text = re.sub(r"https?://cafe\.daum\.net/\S{40,}", "[링크]", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def build_clinical():
    records = []

    for fname, category in CLINICAL_FILES.items():
        path = BASE / fname
        if not path.exists():
            print(f"  [건너뜀] {fname}")
            continue

        df = pd.read_csv(path, encoding="utf-8-sig", dtype=str).fillna("")
        kept = 0

        for _, row in df.iterrows():
            title   = clean_text(row.get("title", ""))
            content = clean_text(row.get("content", ""))
            comments = clean_text(row.get("comments", ""))

            body = content or ""
            if comments:
                body += "\n\n[댓글]\n" + comments

            # 너무 짧거나 내용 없는 것 제외
            if len(body) < 80:
                continue

            text = f"[{category}] {title}\n\n{body}" if title else body

            records.append({
                "type":     "clinical",
                "category": category,
                "title":    title,
                "text":     text,
                "url":      row.get("url", ""),
            })
            kept += 1

        print(f"  {fname}: {len(df)}행 → {kept}건 채택")

    with open(OUT_CLINICAL, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"임상 데이터: {len(records):,}건 → {OUT_CLINICAL.name}")
    return len(records)


# ── 실행 ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("  RAG 데이터셋 빌드")
    print("=" * 50)

    n_rx  = build_prescriptions()
    print()
    n_cli = build_clinical()

    print()
    print("=" * 50)
    total = n_rx + n_cli
    print(f"  완료: 총 {total:,}건")
    print(f"  {OUT_PRESCRIPTIONS.name}: {n_rx:,}건 (처방/약재)")
    print(f"  {OUT_CLINICAL.name}: {n_cli:,}건 (임상 케이스)")
    print("=" * 50)
