import json
import logging
import os

from anthropic import AsyncAnthropic
from dotenv import load_dotenv
from fastapi import HTTPException
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import asyncio

from app.diagnosis.prompt import (
    PROMPT_DIAG_TEMPLATE,
    PROMPT_DIAG_TEMPLATE_GENERAL,
    PROMPT_RX_TEMPLATE,
    PROMPT_RX_TEMPLATE_GENERAL,
    QA_PROMPT_TEMPLATE,
)
from app.diagnosis.anonymize import anonymize

logger = logging.getLogger(__name__)

load_dotenv(override=True)
async_client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

_default_data_dir = os.path.join(os.path.dirname(__file__), "../../../data")
DATA_DIR = os.environ.get("DATA_DIR", _default_data_dir)


def _load_jsonl(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _build_index(records: list[dict], ngram_range: tuple[int, int] = (2, 3)):
    if not records:
        return None, None
    texts = [r["text"] for r in records]
    vec = TfidfVectorizer(analyzer="char", ngram_range=ngram_range)
    matrix = vec.fit_transform(texts)
    return vec, matrix


def _search(query: str, records: list[dict], vec, matrix, n: int) -> str:
    if not records or vec is None:
        return ""
    q_vec = vec.transform([query])
    scores = cosine_similarity(q_vec, matrix).flatten()
    top_idx = scores.argsort()[-n:][::-1]
    return "\n".join(records[i]["text"][:400] for i in top_idx)


_rx_records = _load_jsonl(os.path.join(DATA_DIR, "rag_prescriptions.jsonl"))
_rx_vec, _rx_matrix = _build_index(_rx_records)

# 임상 사례 DB (한의학 임상 사례 + 카페 임상상담 게시글)
# 카페 게시글 추가 후 char 3-gram 어휘가 ~2M개까지 늘어나 빌드 시 OOM이 발생했으므로
# 2-gram만 사용해 어휘 크기를 억제한다.
_cl_records = _load_jsonl(os.path.join(DATA_DIR, "rag_clinical.jsonl")) + _load_jsonl(
    os.path.join(DATA_DIR, "rag_cafe_posts.jsonl")
)
_cl_vec, _cl_matrix = _build_index(_cl_records, ngram_range=(2, 2))

logger.info(
    f"[RAG] 처방 DB {len(_rx_records)}건, 임상 사례 {len(_cl_records)}건 로드 완료"
)


def find_relevant_prescriptions(query: str, n: int = 5) -> str:
    return _search(query, _rx_records, _rx_vec, _rx_matrix, n)


def find_relevant_cases(query: str, n: int = 3) -> str:
    return _search(query, _cl_records, _cl_vec, _cl_matrix, n)


async def _call_claude_async(prompt: str) -> str:
    message = await async_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}],
    )
    text = message.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0]
    return text.strip()


async def _diagnose_from_prompt_async(prompt: str) -> dict:
    for attempt in range(2):
        raw = await _call_claude_async(prompt)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(
                f"[diagnosis] JSON 파싱 실패 (시도 {attempt + 1}/2): {raw[:200]}"
            )

    raise HTTPException(
        status_code=502,
        detail="AI 진단 결과를 파싱할 수 없습니다. 잠시 후 다시 시도해주세요.",
    )


async def diagnose(transcription: str) -> dict:
    anon = anonymize(transcription)
    public_data = find_relevant_prescriptions(anon, n=5)
    cafe_data = find_relevant_cases(anon, n=3)

    dataset_diag_prompt = PROMPT_DIAG_TEMPLATE.format(
        transcription=anon,
        cafe_data=cafe_data or "임상 사례 없음",
    )
    dataset_rx_prompt = PROMPT_RX_TEMPLATE.format(
        transcription=anon,
        public_data=public_data or "DB 데이터 없음",
    )
    general_diag_prompt = PROMPT_DIAG_TEMPLATE_GENERAL.format(transcription=anon)
    general_rx_prompt = PROMPT_RX_TEMPLATE_GENERAL.format(transcription=anon)

    dataset_diag, dataset_rx, general_diag, general_rx = await asyncio.gather(
        _diagnose_from_prompt_async(dataset_diag_prompt),
        _diagnose_from_prompt_async(dataset_rx_prompt),
        _diagnose_from_prompt_async(general_diag_prompt),
        _diagnose_from_prompt_async(general_rx_prompt),
    )
    return {
        "dataset_based": {**dataset_diag, **dataset_rx},
        "claude_based": {**general_diag, **general_rx},
    }


def _build_ask_prompt(question: str) -> str:
    public_data = find_relevant_prescriptions(question, n=5)
    cafe_data = find_relevant_cases(question, n=3)
    return QA_PROMPT_TEMPLATE.format(
        question=question,
        public_data=public_data or "DB 데이터 없음",
        cafe_data=cafe_data or "임상 사례 없음",
    )


async def ask(question: str) -> str:
    return await _call_claude_async(_build_ask_prompt(question))


async def ask_stream(question: str):
    prompt = _build_ask_prompt(question)
    async with async_client.messages.stream(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        async for text in stream.text_stream:
            yield text
