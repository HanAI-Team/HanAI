import re


def anonymize(text: str) -> str:
    # 주민등록번호 (000000-0000000)
    text = re.sub(r"\d{6}-[1-4]\d{6}", "[주민번호]", text)

    # 전화번호 (010-0000-0000, 02-000-0000 등)
    text = re.sub(r"0\d{1,2}-\d{3,4}-\d{4}", "[전화번호]", text)

    # 이메일
    text = re.sub(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "[이메일]", text)

    # 한국 이름 (홍길동 님, 환자 김철수 등 - 호칭 앞 2~4자 한글)
    text = re.sub(r"(?<=환자\s)[가-힣]{2,4}", "[이름]", text)
    text = re.sub(r"[가-힣]{2,4}\s?(?:님|씨|환자)", "[이름]", text)

    return text
