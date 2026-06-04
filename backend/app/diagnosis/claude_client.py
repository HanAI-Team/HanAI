import json
import logging
import os

import anthropic
from dotenv import load_dotenv
from fastapi import HTTPException
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.diagnosis.prompt import PROMPT_TEMPLATE, QA_PROMPT_TEMPLATE
from app.diagnosis.anonymize import anonymize

logger = logging.getLogger(__name__)

load_dotenv(override=True)
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "../../../data"))


def _load_jsonl(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _build_index(records: list[dict]):
    if not records:
        return None, None
    texts = [r["text"] for r in records]
    vec = TfidfVectorizer(analyzer="char", ngram_range=(2, 3))
    matrix = vec.fit_transform(texts)
    return vec, matrix


def _search(query: str, records: list[dict], vec, matrix, n: int) -> str:
    if not records or vec is None:
        return ""
    q_vec = vec.transform([query])
    scores = cosine_similarity(q_vec, matrix).flatten()
    top_idx = scores.argsort()[-n:][::-1]
    return "\n".join(records[i]["text"][:400] for i in top_idx)


# 처방 DB (3,094건)
_rx_records = _load_jsonl(os.path.join(DATA_DIR, "rag_prescriptions.jsonl"))
_rx_vec, _rx_matrix = _build_index(_rx_records)

# 임상 사례 DB (2,505건)
_cl_records = _load_jsonl(os.path.join(DATA_DIR, "rag_clinical.jsonl"))
_cl_vec, _cl_matrix = _build_index(_cl_records)

logger.info(f"[RAG] 처방 DB {len(_rx_records)}건, 임상 사례 {len(_cl_records)}건 로드 완료")


def find_relevant_prescriptions(query: str, n: int = 5) -> str:
    return _search(query, _rx_records, _rx_vec, _rx_matrix, n)


def find_relevant_cases(query: str, n: int = 3) -> str:
    return _search(query, _cl_records, _cl_vec, _cl_matrix, n)


def _call_claude(prompt: str) -> str:
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=3000,
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}],
    )
    text = message.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0]
    return text.strip()


def diagnose(transcription: str) -> dict:
    anon = anonymize(transcription)
    public_data = find_relevant_prescriptions(anon, n=5)
    cafe_data = find_relevant_cases(anon, n=3)

    prompt = PROMPT_TEMPLATE.format(
        transcription=anon,
        public_data=public_data or "DB 데이터 없음",
        cafe_data=cafe_data or "임상 사례 없음",
    )

    for attempt in range(2):
        raw = _call_claude(prompt)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(f"[diagnosis] JSON 파싱 실패 (시도 {attempt + 1}/2): {raw[:200]}")

    raise HTTPException(status_code=502, detail="AI 진단 결과를 파싱할 수 없습니다. 잠시 후 다시 시도해주세요.")


def ask(question: str) -> str:
    public_data = find_relevant_prescriptions(question, n=5)
    cafe_data = find_relevant_cases(question, n=3)

    prompt = QA_PROMPT_TEMPLATE.format(
        question=question,
        public_data=public_data or "DB 데이터 없음",
        cafe_data=cafe_data or "임상 사례 없음",
    )
    return _call_claude(prompt)
