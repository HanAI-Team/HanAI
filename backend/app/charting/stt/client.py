# app/charting/stt/client.py
import json
import logging

import httpx

from app.core.config import settings
from app.pipeline.postprocessor import postprocessor

logger = logging.getLogger(__name__)


class ClovaSpeechClient:
    """
    CLOVA Speech 장문인식 REST API 클라이언트
    - 긴 음성 파일 전체를 한 번에 처리 (청크 분할 불필요)
    - 화자 분리 지원
    - 노이즈 필터링 지원
    - 한의학 용어 키워드 부스팅 지원
    """

    def __init__(self):
        self.secret_key = settings.CLOVA_SECRET_KEY
        self.invoke_url = settings.CLOVA_INVOKE_URL

    def _build_params(self) -> str:
        """API 요청 파라미터 생성"""
        boosting_words = (
            ",".join(postprocessor.glossary) if postprocessor.glossary else ""
        )

        params = {
            "language": "ko-KR",
            "completion": "sync",
            "noiseFiltering": True,
            "diarization": {"enable": True},
        }

        if boosting_words:
            params["boostings"] = [{"words": boosting_words}]

        return json.dumps(params)

    def _parse_segments(self, result: dict) -> str:
        """
        segments 기반 화자 분리 텍스트 생성

        Args:
            result: CLOVA Speech API 응답 JSON

        Returns:
            "[A] 텍스트\n[B] 텍스트" 형태의 화자 분리 텍스트
            segments 없을 경우 전체 텍스트 반환
        """
        segments = result.get("segments", [])

        if not segments:
            logger.warning("[STT] segments 없음 — 전체 텍스트로 대체")
            return result.get("text", "")

        lines = []
        for seg in segments:
            speaker = seg.get("speaker", {}).get("name", "화자")
            text = seg.get("text", "").strip()
            if text:
                lines.append(f"[{speaker}] {text}")

        full_text = "\n".join(lines)
        logger.info(f"[STT] 화자 분리 완료 — {len(segments)}개 세그먼트")
        return full_text


async def transcribe(
    self,
    audio_bytes: bytes,
    filename: str = "audio.mp3",
    content_type: str = "audio/mpeg",
) -> str:
    """
    음성 파일 전체 → 화자 분리 텍스트 변환

    Args:
        audio_bytes: 음성 파일 바이트 (mp3, wav, m4a 등)

    Returns:
        "[A] 텍스트\n[B] 텍스트" 형태의 화자 분리된 전체 텍스트
    """
    if not self.secret_key or not self.invoke_url:
        raise ValueError("CLOVA_SECRET_KEY 또는 CLOVA_INVOKE_URL이 .env에 없습니다")

    if not audio_bytes:
        logger.warning("[STT] 빈 오디오 데이터 수신")
        return ""

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{self.invoke_url}/recognizer/upload",
                headers={"X-CLOVASPEECH-API-KEY": self.secret_key},
                files={
                    "media": (filename, audio_bytes, content_type),
                    "params": (None, self._build_params(), "application/json"),
                },
            )
            response.raise_for_status()
            result = response.json()

        text = self._parse_segments(result)
        logger.info(f"[STT] 변환 완료 — {len(text)}자")
        return text

    except httpx.HTTPStatusError as e:
        logger.error(
            f"[STT] API 오류 status={e.response.status_code} body={e.response.text}"
        )
        raise
    except httpx.TimeoutException:
        logger.error("[STT] API 타임아웃 (300초 초과)")
        raise
    except Exception as e:
        logger.error(f"[STT] 오류: {e}")
        raise


clova_client = ClovaSpeechClient()
