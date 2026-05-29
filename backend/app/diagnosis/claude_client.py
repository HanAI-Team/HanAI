import json
import logging
import pandas as pd
import os
import anthropic
from dotenv import load_dotenv
from fastapi import HTTPException
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from app.diagnosis.prompt import PROMPT_TEMPLATE
from app.diagnosis.anonymize import anonymize

logger = logging.getLogger(__name__)

load_dotenv(override=True)
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "../../../data"))

def load_public_data():
    files = {
        '신계(신장/비뇨기)': os.path.join(DATA_DIR, '신계내과학.csv'),
        '간계(간/담낭)':     os.path.join(DATA_DIR, '간계내과학.csv'),
        '심계(심장/순환)':   os.path.join(DATA_DIR, '심계내과학.csv'),
        '폐계(호흡기)':      os.path.join(DATA_DIR, '폐계내과학.csv'),
        '비계(소화기)':      os.path.join(DATA_DIR, '비계내과학.csv'),
    }
    result = []
    for category, f in files.items():
        if not os.path.exists(f):
            continue
        df = pd.read_csv(f, encoding='utf-8-sig')
        grouped = df.groupby(['처방한글명', '처방한자명', '증상한글명', '일반인설명', '출전']).agg({
            '약재한글명': lambda x: ', '.join(x.dropna().unique()),
        }).reset_index()
        grouped['분류'] = category
        result.append(grouped)

    if not result:
        return ""

    combined = pd.concat(result, ignore_index=True)
    with_symptoms = combined[combined['증상한글명'].notna() & (combined['증상한글명'] != '')]
    lines = []
    for _, row in with_symptoms.iterrows():
        line = f"- [{row['분류']}] {row['처방한글명']}({row['처방한자명']}): 증상={row['증상한글명']}"
        if pd.notna(row['일반인설명']) and row['일반인설명']:
            line += f", 설명={row['일반인설명']}"
        if pd.notna(row['출전']) and row['출전']:
            line += f", 출전={row['출전']}"
        lines.append(line)
    return '\n'.join(lines[:400])


def _load_combined_df() -> pd.DataFrame:
    frames = []

    # 임상자료실 (진단/처방 케이스)
    path1 = os.path.join(DATA_DIR, "cafe_diagnosis_data.csv")
    if os.path.exists(path1):
        df1 = pd.read_csv(path1, encoding='utf-8-sig')
        df1 = df1[df1['board'] == 'ADvi_임상자료실'].copy()
        frames.append(df1)

    # 혈위 검색 결과 (침 처방 특화)
    path2 = os.path.join(DATA_DIR, "cafe_acupuncture_data.csv")
    if os.path.exists(path2):
        df2 = pd.read_csv(path2, encoding='utf-8-sig')
        frames.append(df2)

    # 침처방 검색 결과
    path3 = os.path.join(DATA_DIR, "cafe_침처방_data.csv")
    if os.path.exists(path3):
        df3 = pd.read_csv(path3, encoding='utf-8-sig')
        frames.append(df3)

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)
    df['text'] = df['title'].fillna('') + ' ' + df['content'].fillna('')
    return df.reset_index(drop=True)


_cafe_df = _load_combined_df()
_tfidf = TfidfVectorizer(analyzer='char', ngram_range=(2, 3)) if not _cafe_df.empty else None
_cafe_matrix = _tfidf.fit_transform(_cafe_df['text']) if _tfidf is not None else None


def find_relevant_cases(query: str, n: int = 5) -> str:
    if _cafe_df.empty or _tfidf is None:
        return ""
    query_vec = _tfidf.transform([query])
    scores = cosine_similarity(query_vec, _cafe_matrix).flatten()
    top_idx = scores.argsort()[-n:][::-1]
    lines = []
    for i in top_idx:
        row = _cafe_df.iloc[i]
        snippet = str(row['content'])[:300].replace('\n', ' ').strip()
        lines.append(f"- [{row['title']}] {snippet}")
    return '\n'.join(lines)


PUBLIC_DATA = load_public_data()

def _call_claude(prompt: str) -> str:
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


def diagnose(transcription: str) -> dict:
    cafe_data = find_relevant_cases(transcription)
    prompt = PROMPT_TEMPLATE.format(
        transcription=anonymize(transcription),
        public_data=PUBLIC_DATA if PUBLIC_DATA else "DB 데이터 없음",
        cafe_data=cafe_data if cafe_data else "임상 사례 없음",
    )

    for attempt in range(2):
        raw = _call_claude(prompt)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(f"[diagnosis] JSON 파싱 실패 (시도 {attempt + 1}/2): {raw[:200]}")

    raise HTTPException(status_code=502, detail="AI 진단 결과를 파싱할 수 없습니다. 잠시 후 다시 시도해주세요.")
