# test_pipeline.py
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.charting.stt.client import clova_client
from app.pipeline.deidentifier import deidentifier
from app.pipeline.postprocessor import postprocessor

AUDIO_DIR = Path("tests/audio")


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


async def main():
    target = sys.argv[1] if len(sys.argv) > 1 else None
    files = get_audio_files(target)

    if target:
        print(f"🎙️  파일 테스트: {files[0].name}")
    else:
        print(f"🎙️  총 {len(files)}개 파일 테스트 시작")

    for f in files:
        await test_file(f)

    print("\n✅ 테스트 완료")
    print("💡 오인식된 단어는 data/medical_terms/corrections.json에 추가하세요")


if __name__ == "__main__":
    asyncio.run(main())
