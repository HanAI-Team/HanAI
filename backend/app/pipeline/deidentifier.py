# app/pipeline/deidentifier.py
import re
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# 완전 일치 보호 목록
SAFE_TITLES = frozenset([
    "교수님", "원장님", "의사님", "한의사님", "간호사님",
    "박사님", "실장님", "선생님", "원장", "교수",
    "어머님", "아버님", "어르신", "할머님", "할아버님",
    "보호자", "따님", "아드님",
])

# 조사 포함 패턴 보호
# 예: 한의사님이, 어머님께서, 원장님한테 등
SAFE_TITLE_PATTERN = re.compile(
    r"(?:교수|원장|의사|한의사|간호사|박사|실장|선생|"
    r"어머|아버|할머|할아버)님(?:께서?|한테|에게|을|는|이|가|도|만|의)?"
)


@dataclass
class DeidentifyResult:
    original: str
    cleaned: str
    removed_items: list = field(default_factory=list)


class Deidentifier:
    """
    STT 변환 결과 텍스트 비식별화 레이어
    - Claude 호출 전 개인정보 마스킹 처리
    - 직업 호칭/존칭은 마스킹 제외 (SAFE_TITLES, SAFE_TITLE_PATTERN)
    - 주소 패턴은 실제 지역명으로 제한하여 오탐 방지
    """

    def __init__(self):
        self.patterns = [
            # 주민등록번호
            (re.compile(r"\d{6}-[1-4]\d{6}"), "[주민번호]"),
            # 휴대폰 번호
            (re.compile(r"01[0-9]-?\d{3,4}-?\d{4}"), "[연락처]"),
            # 일반 전화번호
            (re.compile(r"0\d{1,2}-?\d{3,4}-?\d{4}"), "[연락처]"),
            # 이메일
            (re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"), "[이메일]"),
            # 이름 + 호칭 (님/씨/환자 등)
            (re.compile(r"[가-힣]{2,4}\s?(?:님|씨|환자|선생님?)"), "[환자]"),
            # 환자 뒤 이름
            (re.compile(r"(?<=환자\s)[가-힣]{2,4}"), "[이름]"),
            # 생년월일
            (re.compile(r"\d{4}년\s?\d{1,2}월\s?\d{1,2}일생?"), "[생년월일]"),
            # 주소 — 실제 지역명으로 제한하여 오탐 방지
            (re.compile(
                r"(?:서울|부산|대구|인천|광주|대전|울산|세종|"
                r"경기|강원|충북|충남|전북|전남|경북|경남|제주)"
                r"[특별광역자치]*[시도]\s[가-힣]{2,6}[시군구]"
            ), "[주소]"),
            # 차트번호
            (re.compile(r"차트\s?번호\s?\d+"), "[차트번호]"),
        ]

    def _protect_safe_titles(self, text: str) -> tuple[str, dict]:
        """
        직업 호칭 및 존칭을 임시 플레이스홀더로 교체
        비식별화 처리 전 보호 → 처리 후 복원
        """
        protected = text
        placeholders = {}

        # 1. 완전 일치 목록 보호
        for i, title in enumerate(SAFE_TITLES):
            if title in protected:
                placeholder = f"__SAFE_{i}__"
                placeholders[placeholder] = title
                protected = protected.replace(title, placeholder)

        # 2. 조사 포함 패턴 보호 (어머님은, 한의사님이, 원장님께서 등)
        def replace_match(m):
            key = f"__SAFEP_{len(placeholders)}__"
            placeholders[key] = m.group()
            return key

        protected = SAFE_TITLE_PATTERN.sub(replace_match, protected)

        return protected, placeholders

    def _restore_safe_titles(self, text: str, placeholders: dict) -> str:
        """플레이스홀더를 원래 호칭으로 복원"""
        restored = text
        for placeholder, title in placeholders.items():
            restored = restored.replace(placeholder, title)
        return restored

    def process(self, text: str) -> DeidentifyResult:
        """
        STT 텍스트 비식별화 처리

        처리 순서:
        1. 직업 호칭/존칭 임시 보호
        2. 개인정보 패턴 마스킹
        3. 보호된 호칭 복원
        """
        if not text:
            return DeidentifyResult(original=text, cleaned=text)

        # 1. 직업 호칭 임시 보호
        protected, placeholders = self._protect_safe_titles(text)

        # 2. 비식별화 패턴 처리
        cleaned = protected
        removed_items = []

        for pattern, replacement in self.patterns:
            matches = pattern.findall(cleaned)
            if matches:
                removed_items.extend(matches)
                cleaned = pattern.sub(replacement, cleaned)

        # 3. 호칭 복원
        cleaned = self._restore_safe_titles(cleaned, placeholders)

        if removed_items:
            logger.info(f"[Deidentifier] {len(removed_items)}개 항목 마스킹 처리")

        return DeidentifyResult(
            original=text,
            cleaned=cleaned,
            removed_items=removed_items,
        )


deidentifier = Deidentifier()
