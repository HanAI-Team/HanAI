# app/charting/stt/client.py
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class ClovaSpeechClient:
    """
    Clova Speech Recognition (CSR) REST API 클라이언트
    - 방식: REST API 파일 업로드 (청크 방식)
    - 제한: 최대 60초 / 청크
    - 지원 포맷: wav, mp3, flac
    - 사용처: chunker.py에서 청크별로 호출 후 텍스트 합치기
    """

    API_URL = "https://naveropenapi.apigw.ntruss.com/recog/v1/stt"

    def __init__(self):
        # .env에 키가 없으면 인스턴스 생성 시점에 에러 발생
        if not settings.CLOVA_CLIENT_ID or not settings.CLOVA_CLIENT_SECRET:
            raise ValueError("CLOVA_CLIENT_ID 또는 CLOVA_CLIENT_SECRET가 .env에 없습니다")

        self.headers = {
            "X-NCP-APIGW-API-KEY-ID": settings.CLOVA_CLIENT_ID,
            "X-NCP-APIGW-API-KEY": settings.CLOVA_CLIENT_SECRET,
            "Content-Type": "application/octet-stream",
        }

    async def transcribe(
        self,
        audio_bytes: bytes,
        language: str = "Kor",
    ) -> str:
        """
        음성 청크 바이트 -> 텍스트 변환

        Args:
            audio_bytes : wav/mp3 형식의 음성 데이터 (최대 60초)
            language    : 언어 코드 (기본값: Kor)

        Returns:
            변환된 텍스트 문자열

        Raises:
            httpx.HTTPStatusError  : API 호출 실패 (4xx, 5xx)
            httpx.TimeoutException : 30초 이내 응답 없음
        """
        if not audio_bytes:
            logger.warning("[STT] 빈 오디오 데이터 수신 — 변환 건너뜀")
            return ""

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.API_URL,
                    params={"lang": language},
                    headers=self.headers,
                    content=audio_bytes,
                    timeout=30.0,
                )
                response.raise_for_status()
                result = response.json()

            text = result.get("text", "")
            logger.info(f"[STT] 변환 완료 — {len(text)}자")
            return text

        except httpx.HTTPStatusError as e:
            logger.error(
                f"[STT] API 오류 "
                f"status={e.response.status_code} "
                f"body={e.response.text}"
            )
            raise

        except httpx.TimeoutException:
            logger.error("[STT] API 타임아웃 (30초 초과)")
            raise

        except Exception as e:
            logger.error(f"[STT] 예상치 못한 오류: {e}")
            raise


# 앱 전체에서 공유하는 싱글톤 인스턴스
# from app.charting.stt.client import clova_client
clova_client = ClovaSpeechClient()
