# app/pipeline/deidentifier.py
import re
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DeidentifyResult:
    original: str                          # 원본 텍스트 (DB 암호화 저장용)
    cleaned: str                           # 비식별화된 텍스트 (Claude 전송용)
    removed_items: list = field(default_factory=list)  # 제거된 항목 로그


class Deidentifier:
    """
    STT 변환 결과 텍스트 비식별화 레이어
    - Claude 호출 전 개인정보 마스킹 처리
    - 승희 diagnosis/anonymize.py 와 별개로 STT 파이프라인 전용
    """

    def __init__(self):
        self.patterns = [
            # 주민등록번호 (901231-1234567)
            (re.compile(r"\d{6}-[1-4]\d{6}"), "[주민번호]"),

            # 휴대폰 번호 (010-1234-5678)
            (re.compile(r"01[0-9]-?\d{3,4}-?\d{4}"), "[연락처]"),

            # 일반 전화번호 (02-1234-5678)
            (re.compile(r"0\d{1,2}-?\d{3,4}-?\d{4}"), "[연락처]"),

            # 이메일
            (re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"), "[이메일]"),

            # 이름 + 호칭 (홍길동씨, 김철수님, 이영희환자)
            (re.compile(r"[가-힣]{2,4}\s?(?:님|씨|환자|선생님?)"), "[환자]"),

            # 환자 뒤 이름 (환자 홍길동)
            (re.compile(r"(?<=환자\s)[가-힣]{2,4}"), "[이름]"),

            # 생년월일 (1990년 12월 31일생)
            (re.compile(r"\d{4}년\s?\d{1,2}월\s?\d{1,2}일생?"), "[생년월일]"),

            # 주소 (서울시 강남구)
            (re.compile(r"[가-힣]+[시도]\s[가-힣]+[시군구]"), "[주소]"),

            # 차트번호
            (re.compile(r"차트\s?번호\s?\d+"), "[차트번호]"),
        ]

    def process(self, text: str) -> DeidentifyResult:
        """
        텍스트에서 개인정보 마스킹 처리

        Args:
            text: STT 변환 결과 원본 텍스트

        Returns:
            DeidentifyResult (original, cleaned, removed_items)
        """
        cleaned = text
        removed_items = []

        for pattern, replacement in self.patterns:
            matches = pattern.findall(cleaned)
            if matches:
                removed_items.extend(matches)
                cleaned = pattern.sub(replacement, cleaned)

        if removed_items:
            logger.info(f"[Deidentifier] {len(removed_items)}개 항목 마스킹 처리")

        return DeidentifyResult(
            original=text,
            cleaned=cleaned,
            removed_items=removed_items,
        )


# 싱글톤 인스턴스
# from app.pipeline.deidentifier import deidentifier
deidentifier = Deidentifier()
