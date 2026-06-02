# app/pipeline/postprocessor.py
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

CORRECTIONS_PATH = Path(__file__).parent.parent.parent / "data" / "medical_terms" / "corrections.json"
GLOSSARY_PATH = Path(__file__).parent.parent.parent / "data" / "medical_terms" / "glossary.json"


def _load_corrections() -> dict:
    """
    corrections.json 로드
    _comment, _version 등 메타 키(_로 시작) 제외
    """
    try:
        with open(CORRECTIONS_PATH, encoding="utf-8") as f:
            data = json.load(f)

        # _comment, _version 등 메타 키 제외
        corrections = {k: v for k, v in data.items() if not k.startswith("_")}

        logger.info(f"[Postprocessor] 교정 패턴 {len(corrections)}개 로드 완료")
        return corrections
    except FileNotFoundError:
        logger.warning(f"[Postprocessor] corrections.json 없음: {CORRECTIONS_PATH}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"[Postprocessor] corrections.json 파싱 오류: {e}")
        return {}


def _load_glossary() -> list:
    """glossary.json 로드"""
    try:
        with open(GLOSSARY_PATH, encoding="utf-8") as f:
            data = json.load(f)
        terms = data.get("terms", [])
        logger.info(f"[Postprocessor] 한의학 용어 {len(terms)}개 로드 완료")
        return terms
    except FileNotFoundError:
        logger.warning(f"[Postprocessor] glossary.json 없음: {GLOSSARY_PATH}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"[Postprocessor] glossary.json 파싱 오류: {e}")
        return []


class Postprocessor:
    """
    STT 변환 텍스트 후처리기
    - corrections.json 기반 한의학 용어 오인식 교정
    - 비식별화 이후, Claude 호출 이전 단계에서 실행
    """

    def __init__(self):
        self.corrections = _load_corrections()
        self.glossary = _load_glossary()

    def correct(self, text: str) -> str:
        """
        오인식된 한의학 용어 교정

        Args:
            text: 비식별화된 STT 텍스트

        Returns:
            교정된 텍스트
        """
        if not text:
            return text

        corrected = text
        applied = []

        for wrong, right in self.corrections.items():
            if wrong in corrected:
                corrected = corrected.replace(wrong, right)
                applied.append(f"{wrong} → {right}")

        if applied:
            logger.info(f"[Postprocessor] {len(applied)}개 교정 적용: {applied}")

        return corrected

    def reload(self) -> None:
        """
        corrections.json 실시간 리로드
        베타 테스트 중 용어 추가 시 서버 재시작 없이 반영 가능
        """
        self.corrections = _load_corrections()
        self.glossary = _load_glossary()
        logger.info("[Postprocessor] 데이터 리로드 완료")


# 싱글톤 인스턴스
# from app.pipeline.postprocessor import postprocessor
postprocessor = Postprocessor()
