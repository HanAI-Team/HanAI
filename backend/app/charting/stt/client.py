# app/charting/stt/client.py
"""VITO(RTZR) Speech STT 클라이언트.

2026-07-20 CLOVA에서 전환 — scripts/compare_stt_vito_vs_clova.py로 실제 진료
음성 8건을 비교 검증해 VITO가 CLOVA 대비 약 40% 저렴하면서 최종 AI 진단
결과(응급 여부/사상체질/처방)에 실질적 차이가 없음을 확인했다
(scripts/compare_diagnosis_vito_vs_clova.py).

CLOVA 구현은 롤백 대비 app/charting/stt/clova_client.py에 그대로 보존돼 있다.
"""
import asyncio
import io
import json
import logging
import os
import time

import httpx
import mutagen
from langfuse import get_client

from app.charting.stt.vad import trim_silence
from app.core.config import settings

logger = logging.getLogger(__name__)

MIME_MAP = {
    "mp3": "audio/mpeg",
    "m4a": "audio/mp4",
    "wav": "audio/wav",
    "ogg": "audio/ogg",
    "flac": "audio/flac",
    "aac": "audio/aac",
}

RTZR_AUTH_URL = "https://openapi.vito.ai/v1/authenticate"
RTZR_TRANSCRIBE_URL = "https://openapi.vito.ai/v1/transcribe"
RTZR_POLL_INTERVAL_SEC = 5
RTZR_POLL_TIMEOUT_SEC = 900

VITO_WON_PER_HOUR = 1000  # 2026-07-20 실측 요율 (T1 구간, 0~1,000시간)
VITO_MIN_CHARGE_SEC = 10  # 10초 미만은 10초로 집계
KRW_TO_USD_RATE = 1350  # 대략적인 환율, 필요시 조정

VITO_KEYWORD_LIMIT = 500
GLOSSARY_PATH = os.path.join(
    os.path.dirname(__file__), "../../../data/medical_terms/glossary.json"
)


def _vito_cost_usd(duration_seconds: float) -> float:
    billed_seconds = max(duration_seconds, VITO_MIN_CHARGE_SEC)
    won = (billed_seconds / 3600) * VITO_WON_PER_HOUR
    return won / KRW_TO_USD_RATE


def _audio_duration_seconds(audio_bytes: bytes) -> float:
    try:
        audio = mutagen.File(io.BytesIO(audio_bytes))
        return audio.info.length if audio is not None else 0.0
    except Exception as e:
        logger.warning(f"[STT] 오디오 길이 계산 실패: {e}")
        return 0.0


def load_vito_keywords(limit: int = VITO_KEYWORD_LIMIT) -> list[str]:
    """glossary.json의 priority(무조건 포함) + auto(짧은 순으로 슬롯 채움)를
    postprocessor._load_glossary()와 동일한 원칙으로 limit개까지 구성한다.
    (postprocessor.py는 CLOVA_LIMIT=1000이 하드코딩되어 있어 VITO의 500개
    제한에는 그대로 재사용할 수 없어 독립적으로 구현했다 — VITO 검증에 쓰인
    scripts/compare_stt_vito_vs_clova.py의 load_vito_keywords()와 동일 로직.)
    """
    try:
        with open(GLOSSARY_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning(f"[STT] glossary.json 로드 실패, 키워드 부스팅 없이 진행: {e}")
        return []

    priority = data.get("priority", [])
    auto = data.get("auto", [])
    priority_set = set(priority)
    auto_filtered = sorted([t for t in auto if t not in priority_set], key=len)
    return (priority + auto_filtered)[:limit]


class VitoSpeechClient:
    def __init__(self):
        self.client_id = settings.RTZR_CLIENT_ID
        self.client_secret = settings.RTZR_CLIENT_SECRET
        self._keywords: list[str] | None = None

    def _get_keywords(self) -> list[str]:
        if self._keywords is None:
            self._keywords = load_vito_keywords()
            logger.info(f"[STT] VITO 키워드 부스팅 {len(self._keywords)}개 로드")
        return self._keywords

    async def _get_token(self, client: httpx.AsyncClient) -> str:
        response = await client.post(
            RTZR_AUTH_URL,
            data={"client_id": self.client_id, "client_secret": self.client_secret},
        )
        response.raise_for_status()
        return response.json()["access_token"]

    async def _submit(
        self,
        client: httpx.AsyncClient,
        token: str,
        audio_bytes: bytes,
        filename: str,
        mime_type: str,
        keywords: list[str],
    ) -> httpx.Response:
        config = {
            "model_name": "sommers",
            "use_diarization": True,
            "domain": "GENERAL",  # "MEETING"은 지원 안 됨, "CALL"은 전화 통화 전용이라 부적합
            "keywords": keywords,
        }
        return await client.post(
            RTZR_TRANSCRIBE_URL,
            headers={"Authorization": f"Bearer {token}"},
            files={"file": (filename, audio_bytes, mime_type)},
            data={"config": json.dumps(config)},
        )

    def _parse_segments(self, result: dict) -> str:
        utterances = result.get("results", {}).get("utterances", [])

        if not utterances:
            logger.warning("[STT] utterances 없음")
            return ""

        lines = []
        for u in utterances:
            spk = u.get("spk")
            msg = u.get("msg", "").strip()
            if msg:
                lines.append(f"[화자{spk}] {msg}")

        full_text = "\n".join(lines)
        speakers = {u.get("spk") for u in utterances}
        logger.info(f"[STT] 화자 분리 완료 — 화자 {len(speakers)}명, {len(utterances)}개 세그먼트")
        return full_text

    async def _submit_with_keyword_fallback(
        self,
        client: httpx.AsyncClient,
        token: str,
        audio_bytes: bytes,
        filename: str,
        mime_type: str,
        keywords: list[str],
    ) -> httpx.Response:
        try:
            response = await self._submit(client, token, audio_bytes, filename, mime_type, keywords)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400 and any(" " in w for w in keywords):
                logger.warning(
                    f"[STT] VITO keywords 거부됨(400) — 공백 포함 단어 공백 제거 후 재시도: {e.response.text[:300]}"
                )
                fallback_keywords = [w.replace(" ", "") for w in keywords]
                response = await self._submit(client, token, audio_bytes, filename, mime_type, fallback_keywords)
                response.raise_for_status()
                return response
            raise

    async def _poll_until_done(self, client: httpx.AsyncClient, token: str, transcribe_id: str) -> dict:
        start = time.monotonic()
        while True:
            await asyncio.sleep(RTZR_POLL_INTERVAL_SEC)
            poll_response = await client.get(
                f"{RTZR_TRANSCRIBE_URL}/{transcribe_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            poll_response.raise_for_status()
            result = poll_response.json()
            status = result.get("status")
            if status == "completed":
                return result
            if status == "failed":
                raise RuntimeError(f"VITO 전사 실패: {result}")
            if time.monotonic() - start > RTZR_POLL_TIMEOUT_SEC:
                raise TimeoutError(f"VITO 전사 폴링 타임아웃 (id={transcribe_id})")

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.mp3") -> str:
        if not self.client_id or not self.client_secret:
            raise ValueError("RTZR_CLIENT_ID 또는 RTZR_CLIENT_SECRET이 .env에 없습니다")

        if not audio_bytes:
            logger.warning("[STT] 빈 오디오 데이터 수신")
            return ""

        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "mp3"
        mime_type = MIME_MAP.get(ext, "audio/mpeg")
        file_name = f"audio.{ext}"
        logger.info(f"[STT] 파일명={file_name}, MIME={mime_type}")

        audio_bytes = await asyncio.to_thread(trim_silence, audio_bytes, ext)
        keywords = self._get_keywords()

        try:
            duration_seconds = _audio_duration_seconds(audio_bytes)
            with get_client().start_as_current_observation(
                as_type="generation",
                name="vito-speech-stt",
                model="sommers",
            ) as gen:
                async with httpx.AsyncClient(timeout=300.0) as client:
                    token = await self._get_token(client)
                    submit_response = await self._submit_with_keyword_fallback(
                        client, token, audio_bytes, file_name, mime_type, keywords
                    )
                    transcribe_id = submit_response.json()["id"]
                    result = await self._poll_until_done(client, token, transcribe_id)

                text = self._parse_segments(result)
                gen.update(
                    usage_details={"audio_seconds": duration_seconds},
                    cost_details={"total": _vito_cost_usd(duration_seconds)},
                )

            logger.info(f"[STT] 변환 완료 — {len(text)}자")
            return text

        except httpx.HTTPStatusError as e:
            logger.error(f"[STT] API 오류 status={e.response.status_code} body={e.response.text}")
            raise
        except httpx.TimeoutException:
            logger.error("[STT] API 타임아웃")
            raise
        except Exception as e:
            logger.error(f"[STT] 오류: {e}")
            raise


vito_client = VitoSpeechClient()
