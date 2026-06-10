# app/charting/stt/client.py
import json
import logging

import httpx

from app.core.config import settings
from app.pipeline.postprocessor import postprocessor

logger = logging.getLogger(__name__)

MIME_MAP = {
    "mp3": "audio/mpeg",
    "m4a": "audio/mp4",
    "wav": "audio/wav",
    "ogg": "audio/ogg",
    "flac": "audio/flac",
    "aac": "audio/aac",
}


class ClovaSpeechClient:
    def __init__(self):
        self.secret_key = settings.CLOVA_SECRET_KEY
        self.invoke_url = settings.CLOVA_INVOKE_URL

    def _build_params(self) -> str:
        params = {
            "language": "ko-KR",
            "completion": "sync",
            "noiseFiltering": True,
            "diarization": {
                "enable": True
            },
        }
        if postprocessor.glossary:
        # CLOVA boostings 최대 1,000개 제한
            limited_glossary = postprocessor.glossary[:1000]
            params["boostings"] = [{"words": word} for word in limited_glossary]
            logger.info(f"[STT] boostings 적용 — {len(limited_glossary)}개")

        return json.dumps(params)

    def _parse_segments(self, result: dict) -> str:
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

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.mp3") -> str:
        if not self.secret_key or not self.invoke_url:
            raise ValueError("CLOVA_SECRET_KEY 또는 CLOVA_INVOKE_URL이 .env에 없습니다")

        if not audio_bytes:
            logger.warning("[STT] 빈 오디오 데이터 수신")
            return ""

        # 파일 확장자로 MIME 타입 결정
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "mp3"
        mime_type = MIME_MAP.get(ext, "audio/mpeg")
        file_name = f"audio.{ext}"
        logger.info(f"[STT] 파일명={file_name}, MIME={mime_type}")

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.invoke_url}/recognizer/upload",
                    headers={"X-CLOVASPEECH-API-KEY": self.secret_key},
                    files={
                        "media": (file_name, audio_bytes, mime_type),
                        "params": (None, self._build_params(), "application/json"),
                    }
                )
                response.raise_for_status()
                result = response.json()

            text = self._parse_segments(result)
            logger.info(f"[STT] 변환 완료 — {len(text)}자")
            return text

        except httpx.HTTPStatusError as e:
            logger.error(f"[STT] API 오류 status={e.response.status_code} body={e.response.text}")
            raise
        except httpx.TimeoutException:
            logger.error("[STT] API 타임아웃 (300초 초과)")
            raise
        except Exception as e:
            logger.error(f"[STT] 오류: {e}")
            raise


clova_client = ClovaSpeechClient()
