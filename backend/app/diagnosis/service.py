from app.diagnosis.claude_client import diagnose


def run_diagnosis(transcription: str) -> str:
    return diagnose(transcription)
