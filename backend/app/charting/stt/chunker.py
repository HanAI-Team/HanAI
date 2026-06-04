# app/charting/stt/chunker.py
import io
import logging

from pydub import AudioSegment

from app.charting.stt.client import clova_client

logger = logging.getLogger(__name__)

# CSR API 제한 60초보다 여유있게 55초로 설정
CHUNK_MS = 55 * 1000


async def transcribe_chunks(audio_bytes: bytes, format: str = "mp3") -> str:
    """
    음성 파일을 55초 단위로 분할 후 순서대로 STT 처리

    Args:
        audio_bytes : 전체 음성 파일 바이트
        format      : 오디오 포맷 (mp3, wav, webm 등)
                      service.py에서 파일명 기반으로 전달

    Returns:
        전체 변환 텍스트 (청크 순서대로 합친 결과)

    Raises:
        Exception: 오디오 로드 실패 또는 STT 오류 시
    """
    if clova_client is None:
        logger.warning("[Chunker] CLOVA 키 없음 — STT 스킵")
        return ""
    # 1. 오디오 로드
    try:
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format=format)
    except Exception as e:
        logger.error(f"[Chunker] 오디오 로드 실패: {e}")
        raise

    total_ms = len(audio)
    logger.info(f"[Chunker] 총 길이: {total_ms / 1000:.1f}초")

    # 2. 55초 이하면 청크 분할 없이 바로 처리
    if total_ms <= CHUNK_MS:
        logger.info("[Chunker] 55초 이하 — 직접 처리")
        buf = io.BytesIO()
        audio.export(buf, format="wav")
        return await clova_client.transcribe(buf.getvalue())

    # 3. 55초 단위로 분할
    chunks = []
    for start_ms in range(0, total_ms, CHUNK_MS):
        end_ms = min(start_ms + CHUNK_MS, total_ms)
        chunks.append(audio[start_ms:end_ms])

    logger.info(f"[Chunker] {len(chunks)}개 청크로 분할")

    # 4. 청크별 STT 처리
    results = []
    for i, chunk in enumerate(chunks):
        buf = io.BytesIO()
        chunk.export(buf, format="wav")
        chunk_bytes = buf.getvalue()

        text = await clova_client.transcribe(chunk_bytes, language="Kor")
        logger.info(f"[Chunker] 청크 {i + 1}/{len(chunks)} 완료 — {len(text)}자")
        results.append(text)

    # 5. 텍스트 합치기
    full_text = " ".join(results)
    logger.info(f"[Chunker] 전체 변환 완료 — {len(full_text)}자")
    return full_text
