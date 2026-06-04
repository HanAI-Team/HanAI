# diagnosis/anonymize.py
from app.pipeline.deidentifier import deidentifier

# STT 파이프라인(app/pipeline/deidentifier.py)과 공통 모듈 사용
# 텍스트 직접 입력 진단 경로 전용 (diagnosis/router.py → claude_client.py)
def anonymize(text: str) -> str:
    return deidentifier.process(text).cleaned
