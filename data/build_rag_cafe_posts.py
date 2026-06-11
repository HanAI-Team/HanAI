"""
Daum 카페 게시글(cafe_posts.json) → RAG 클리닉 데이터셋 변환
출력: rag_cafe_posts.jsonl
"""

import json
import re
from pathlib import Path

BASE = Path(__file__).parent
SRC = BASE / "cafe_posts.json"
OUT = BASE / "rag_cafe_posts.jsonl"

GRPID = "fjM0"
FLDID = "AE8I"

BOILERPLATE = re.compile(
    r"(%?양\s*)?(의사\s*)?대리수술/\s*성범죄\s*/마약처방/실비사기[^\n]*\n?|"
    r"%성분명처방[^\n]*\n?|"
    r"\d?\.?\s*에디터에서\s*<>?\s*html\s*을?\s*(클릭하세요|클릭합니다)[^\n]*\n?|"
    r"\d?\.?\s*아래\s*보안소스를?\s*복사하여\s*html삽입창에\s*넣고\s*확인(\s*버튼)?을?\s*(누릅니다|클릭합니다|클릭하세요)[^\n]*\n?|"
    r"<link[^>]*hanicodi[^>]*>|"
    r"[^\n]*hanicodi[^\n]*\n?|"
    r"[^\n]*대리수술[^\n]*\n?|"
    r"%양\n?|"
    r"🍃\s*한의원에서\s*살아남기.*?open\.kakao\.com",
    re.IGNORECASE | re.DOTALL,
)


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\xa0", " ")
    text = BOILERPLATE.sub("", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def build():
    posts = json.loads(SRC.read_text(encoding="utf-8"))

    records = []
    for p in posts:
        title = clean_text(p.get("title", ""))
        body = clean_text(p.get("body", ""))

        comment_text = "\n".join(
            c["text"].strip() for c in p.get("comments", []) if c.get("text", "").strip()
        )
        comment_text = clean_text(comment_text)

        full_body = body
        if comment_text:
            full_body += "\n\n[댓글]\n" + comment_text

        # 너무 짧거나 내용 없는 것 제외
        if len(full_body) < 80:
            continue

        text = f"[임상상담] {title}\n\n{full_body}" if title else full_body

        records.append({
            "type": "clinical",
            "category": "임상상담",
            "title": title,
            "text": text,
            "url": f"https://cafe.daum.net/_c21_/bbs_read?grpid={GRPID}&fldid={FLDID}&datanum={p['datanum']}",
        })

    with open(OUT, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"카페 게시글: {len(posts):,}개 → {len(records):,}건 채택 → {OUT.name}")


if __name__ == "__main__":
    build()
