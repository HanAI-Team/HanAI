import pandas as pd
import os
import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def load_public_data():
    files = {
        '신계(신장/비뇨기)': 'data/신계내과학.csv',
        '간계(간/담낭)': 'data/간계내과학.csv',
        '심계(심장/순환)': 'data/심계내과학.csv',
        '폐계(호흡기)': 'data/폐계내과학.csv',
        '비계(소화기)': 'data/비계내과학.csv',
    }
    result = []
    for category, f in files.items():
        if not os.path.exists(f):
            continue
        try:
            df = pd.read_csv(f, encoding='utf-8')
        except:
            df = pd.read_csv(f, encoding='cp949')
        grouped = df.groupby(['처방한글명', '처방한자명', '증상한글명', '일반인설명', '출전']).agg({
            '약재한글명': lambda x: ', '.join(x.dropna().unique()),
        }).reset_index()
        grouped['분류'] = category
        result.append(grouped)
    if not result:
        return ""
    combined = pd.concat(result, ignore_index=True)
    with_symptoms = combined[combined['증상한글명'].notna()]
    lines = []
    for _, row in with_symptoms.iterrows():
        line = f"- [{row['분류']}] {row['처방한글명']}({row['처방한자명']}): 증상={row['증상한글명']}"
        if pd.notna(row['일반인설명']):
            line += f", 설명={row['일반인설명']}"
        if pd.notna(row['출전']):
            line += f", 출전={row['출전']}"
        lines.append(line)
    return '\n'.join(lines[:400])

PUBLIC_DATA = load_public_data()

def diagnose(symptoms):
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": f"""당신은 한의학 전문 AI 진단 보조 시스템입니다.
아래 처방 데이터를 참고하여 환자 증상을 분석해주세요.

[공공데이터 처방 DB - 한의대 교과서 처방]
{PUBLIC_DATA}

환자 증상: {symptoms}

다음 형식으로 답변해주세요:
1. 사상체질: (태양인/태음인/소양인/소음인)
2. 진단:
3. 한약 처방 추천: (처방명 + 근거 출전 포함)
4. 생활 습관 조언:

모든 처방은 참고용이며 최종 판단은 한의사 선생님께서 하셔야 합니다."""
            }
        ]
    )
    return message.content[0].text