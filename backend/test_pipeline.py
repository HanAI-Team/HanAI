# test_pipeline.py
import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from app.charting.stt.client import clova_client
from app.pipeline.deidentifier import deidentifier
from app.pipeline.postprocessor import postprocessor

AUDIO_DIR = Path("tests/audio")
pytestmark = pytest.mark.skip(reason="실제 Clova API 필요 - 수동 실행 전용")


def get_audio_files(target: str = None) -> list[Path]:
    supported = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}

    if target:
        path = AUDIO_DIR / target
        if not path.exists():
            matches = list(AUDIO_DIR.glob(f"{target}*"))
            if not matches:
                print(f"❌ 파일을 찾을 수 없습니다: {target}")
                print(f"   경로: {AUDIO_DIR.absolute()}")
                sys.exit(1)
            path = matches[0]
        return [path]

    files = sorted([f for f in AUDIO_DIR.iterdir() if f.suffix.lower() in supported])
    if not files:
        print(f"❌ {AUDIO_DIR}/ 폴더에 오디오 파일이 없습니다")
        sys.exit(1)
    return files


async def test_file(audio_path: Path):
    print("\n" + "=" * 60)
    print(f"📁 파일: {audio_path.name}")
    print("=" * 60)

    audio_bytes = audio_path.read_bytes()

    # STEP 1. STT
    print("\n📌 STEP 1. STT 변환")
    print("-" * 40)
    stt_result = await clova_client.transcribe(audio_bytes)
    print(f"결과: {stt_result}")

    # STEP 2. 비식별화
    print("\n📌 STEP 2. 비식별화")
    print("-" * 40)
    deidentify_result = deidentifier.process(stt_result)
    print(f"결과: {deidentify_result.cleaned}")
    if deidentify_result.removed_items:
        print(f"🔴 마스킹된 항목: {deidentify_result.removed_items}")
    else:
        print("✅ 마스킹 항목 없음")

    # STEP 3. 용어 교정
    print("\n📌 STEP 3. 한의학 용어 교정")
    print("-" * 40)
    corrected = postprocessor.correct(deidentify_result.cleaned)
    print(f"결과: {corrected}")

    # 변경사항 비교
    if stt_result != corrected:
        print("\n🔍 전체 변경사항 있음")
    else:
        print("\n✅ 변경사항 없음")

    # glossary 용어 체크
    print("\n📌 오인식 의심 단어 체크")
    print("-" * 40)
    found = [term for term in postprocessor.glossary if term in corrected]
    if found:
        print(f"✅ 정상 인식된 한의학 용어: {found}")
    else:
        print("⚠️  glossary 용어가 결과에 없음 — 오인식 가능성 확인 필요")

    print("=" * 60)
    return corrected


async def test_diagnose(corrected: str):
    from app.diagnosis.claude_client import diagnose
    print("\n📌 STEP 4. Claude 진단 (이름 마스킹 포함)")
    print("-" * 40)
    print("⏳ Claude API 호출 중...")
    try:
        result = await diagnose(corrected)
        constitution = (result.get("sasang_constitution") or {}).get("type", "-")
        tkm = (result.get("tkm_diagnosis") or {}).get("diagnosis_name", "-")
        herb = (result.get("herbal_prescription") or {})
        herb_name = herb.get("name_kr", "-")
        acu = result.get("acupuncture_prescription") or []
        acu_str = ", ".join(p.get("point_kr", "") for p in acu if p.get("point_kr"))
        print(f"사상체질: {constitution}")
        print(f"진단명:   {tkm}")
        print(f"처방명:   {herb_name}")
        print(f"침 처방:  {acu_str or '-'}")
        alert = result.get("emergency_alert") or {}
        if alert.get("is_emergency"):
            print(f"🚨 응급: {alert.get('reason')}")
    except Exception as e:
        print(f"❌ Claude 오류: {e}")
    print("=" * 60)


async def main():
    run_diagnose = "--diagnose" in sys.argv or "-d" in sys.argv
    args = [a for a in sys.argv[1:] if a not in ("--diagnose", "-d")]
    target = args[0] if args else None
    files = get_audio_files(target)

    if target:
        print(f"🎙️  파일 테스트: {files[0].name}")
    else:
        print(f"🎙️  총 {len(files)}개 파일 테스트 시작")

    for f in files:
        corrected = await test_file(f)
        if run_diagnose and corrected:
            await test_diagnose(corrected)

    print("\n✅ 테스트 완료")
    print("💡 오인식된 단어는 data/medical_terms/corrections.json에 추가하세요")
    if not run_diagnose:
        print("💡 Claude 진단까지 테스트하려면 --diagnose 플래그를 추가하세요")


if __name__ == "__main__":
    asyncio.run(main())
