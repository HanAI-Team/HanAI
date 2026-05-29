from app.diagnosis.claude_client import diagnose


def run_diagnosis(transcription: str) -> dict:
    return diagnose(transcription)
