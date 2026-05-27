import pandas as pd
import os
import anthropic
from dotenv import load_dotenv

load_dotenv(override=True)
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "../../../../data"))

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


PUBLIC_DATA = load_public_data()

PROMPT_TEMPLATE = """당신은 한의학 전문 AI 진료 보조입니다.
아래 진료 내용을 분석해서 반드시 다섯 가지를 함께 제공해주세요.

진료 내용:
{transcription}

[참고: 한의대 교과서 처방 DB]
{public_data}

1. 사상체질 판별
   - 체질: (태양인 / 태음인 / 소양인 / 소음인)
   - 판단 근거: (증상, 체형, 성격 등 근거 명시)

2. 한의학적 진단
   - 진단명: (변증 포함)
   - 병인병기: (발병 원인과 기전)

3. 양방 진단명
   - 대응되는 서양의학 진단명 (ICD 코드 포함 가능 시)

4. 한약 처방 추천
   - 처방명 (한글 + 한자)
   - 약재 구성 + 용량
   - 출전
   - 처방 선택 근거

5. 침 처방 추천
   - 주요 혈위 목록
   - 각 혈위 위치
   - 취혈 근거

모든 내용은 참고용이며 최종 판단은 한의사가 직접 합니다."""


def diagnose(transcription: str) -> str:
    prompt = PROMPT_TEMPLATE.format(
        transcription=transcription,
        public_data=PUBLIC_DATA,
    )
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text
