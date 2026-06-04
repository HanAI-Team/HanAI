# app/charting/stt/chunker.py
import logging

from app.charting.stt.client import clova_client

logger = logging.getLogger(__name__)


async def transcribe_chunks(audio_bytes: bytes, format: str = "mp3") -> str:
    """
    음성 파일 → 텍스트 변환
    CLOVA Speech 장문인식 사용 (청크 분할 불필요)

    Args:
        audio_bytes : 전체 음성 파일 바이트
        format      : 오디오 포맷 (사용하지 않음, 호환성 유지용)

    Returns:
        전체 변환 텍스트
    """
    logger.info(f"[Chunker] 음성 파일 수신 — {len(audio_bytes) / 1024:.1f}KB")
    return await clova_client.transcribe(audio_bytes)
