import logging

from app.charting.stt.client import clova_client

logger = logging.getLogger(__name__)


async def transcribe_chunks(audio_bytes: bytes, format: str = "mp3") -> str:
    logger.info(f"[Chunker] 음성 파일 수신 — {len(audio_bytes) / 1024:.1f}KB")

    content_type_map = {
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "m4a": "audio/mp4",
        "webm": "audio/webm",
    }
    content_type = content_type_map.get(format, "audio/mpeg")
    filename = f"audio.{format}"

    return await clova_client.transcribe(
        audio_bytes, filename=filename, content_type=content_type
    )
