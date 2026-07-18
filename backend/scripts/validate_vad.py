"""
VAD(Silero-VAD) 정확도 검증 스크립트 — 실제 STT 파이프라인에는 적용하지 않는 독립 스크립트.

~/Desktop/zinmac/진료녹음/ 아래 실제 진료 음성 6개(m4a)를 대상으로,
silero-vad가 발화/무음 구간을 얼마나 정확히 나누는지 확인한다.

m4a -> WAV 디코딩은 ffmpeg가 로컬에 없어서(torchaudio.load가 이 환경에서
torchcodec/ffmpeg 공유 라이브러리에 의존해 실패함), macOS 내장 `afconvert`
(ffmpeg 아님, Apple CoreAudio 커맨드라인 도구)로 16kHz mono PCM WAV를
만든 뒤 표준 라이브러리 `wave` 모듈로 직접 읽어 torch 텐서로 변환한다.
silero-vad의 `get_speech_timestamps()`는 파일 경로가 아니라 1차원
float torch.Tensor를 받으므로 이 방식으로 torchaudio/torchcodec를
완전히 우회할 수 있다.

실행: uv run python scripts/validate_vad.py
"""
import os
import struct
import subprocess
import sys
import tempfile

import torch
from silero_vad import get_speech_timestamps, load_silero_vad

AUDIO_DIR = os.path.expanduser("~/Desktop/zinmac/진료녹음")
FILES = [
    "김혜수 인천 산후조리 약.m4a",
    "앙서희 환자.m4a",
    "정현성 환자.m4a",
    "지훈 부정맥 환자.m4a",
    "TalkFile_박황우 전주 한자.m4a.m4a",
    "TalkFile_배정자 전주 환자 상담.m4a.m4a",
]

SAMPLE_RATE = 16000
MIN_SILENCE_SEC = 10.0
WON_PER_SEC = (5 + 2) / 15  # 음성인식 5원 + 화자인식 2원, 15초당


def m4a_to_wav(src_path: str, dst_path: str) -> None:
    subprocess.run(
        ["afconvert", "-d", f"LEI16@{SAMPLE_RATE}", "-c", "1", "-f", "WAVE", src_path, dst_path],
        check=True,
        capture_output=True,
    )


def read_wav_as_tensor(wav_path: str) -> torch.Tensor:
    """RIFF/data 청크를 직접 파싱한다.

    afconvert가 만드는 WAV는 WAVE_FORMAT_EXTENSIBLE(포맷 태그 65534) 헤더를
    쓰는데, 표준 라이브러리 `wave` 모듈이 이 태그를 지원하지 않아 직접
    파싱한다. 우리가 afconvert에 -d LEI16@16000 -c 1로 지정했으므로
    data 청크의 실제 샘플은 16kHz mono 16bit little-endian PCM으로 고정.
    """
    with open(wav_path, "rb") as f:
        data = f.read()
    assert data[:4] == b"RIFF" and data[8:12] == b"WAVE"
    pos = 12
    pcm_bytes = None
    while pos + 8 <= len(data):
        chunk_id = data[pos : pos + 4]
        chunk_size = struct.unpack("<I", data[pos + 4 : pos + 8])[0]
        chunk_start = pos + 8
        if chunk_id == b"data":
            pcm_bytes = data[chunk_start : chunk_start + chunk_size]
            break
        pos = chunk_start + chunk_size + (chunk_size % 2)
    if pcm_bytes is None:
        raise ValueError(f"data 청크를 찾을 수 없음: {wav_path}")
    samples = torch.frombuffer(bytearray(pcm_bytes), dtype=torch.int16)
    return samples.float() / 32768.0


def fmt_mmss(seconds: float) -> str:
    m, s = divmod(int(round(seconds)), 60)
    return f"{m}:{s:02d}"


def compute_frame_probs(audio: torch.Tensor, model, window_size_samples: int = 512) -> list[float]:
    """get_speech_timestamps 내부와 동일한 512-sample 윈도우로 프레임별 발화 확률을 직접 계산한다.

    목적: "발화"로 판정된 구간이 실제로 확신도 높은 발화인지, 아니면
    threshold(0.5) 근처의 애매한 확률(=배경소음을 발화로 오판했을 가능성)인지
    통계적으로 걸러내기 위함. 실제로 들어보지 않고는 100% 확신할 수 없으므로
    이건 "의심 구간 후보"를 좁혀주는 보조 지표일 뿐이다.
    """
    model.reset_states()
    probs = []
    for start in range(0, len(audio), window_size_samples):
        chunk = audio[start : start + window_size_samples]
        if len(chunk) < window_size_samples:
            chunk = torch.nn.functional.pad(chunk, (0, window_size_samples - len(chunk)))
        probs.append(model(chunk, SAMPLE_RATE).item())
    return probs


def segment_avg_confidence(seg: dict, probs: list[float], window_size_samples: int = 512) -> float:
    start_idx = int(seg["start"] * SAMPLE_RATE / window_size_samples)
    end_idx = max(start_idx + 1, int(seg["end"] * SAMPLE_RATE / window_size_samples))
    window = probs[start_idx:end_idx]
    return sum(window) / len(window) if window else 0.0


def find_silence_gaps(speech_segments: list[dict], total_duration: float) -> list[tuple[float, float]]:
    gaps = []
    cursor = 0.0
    for seg in speech_segments:
        if seg["start"] - cursor > 0:
            gaps.append((cursor, seg["start"]))
        cursor = seg["end"]
    if total_duration - cursor > 0:
        gaps.append((cursor, total_duration))
    return gaps


def main():
    print("silero-vad 모델 로딩...")
    model = load_silero_vad()

    results = []
    tmpdir = tempfile.mkdtemp(prefix="vad_validate_")

    for fname in FILES:
        src = os.path.join(AUDIO_DIR, fname)
        if not os.path.exists(src):
            print(f"[SKIP] 파일 없음: {src}")
            continue

        wav_path = os.path.join(tmpdir, "tmp.wav")
        m4a_to_wav(src, wav_path)
        audio = read_wav_as_tensor(wav_path)
        total_duration = len(audio) / SAMPLE_RATE

        speech_ts = get_speech_timestamps(
            audio,
            model,
            sampling_rate=SAMPLE_RATE,
            min_silence_duration_ms=100,
            return_seconds=True,
        )

        frame_probs = compute_frame_probs(audio, model)
        low_confidence_segs = []
        for seg in speech_ts:
            conf = segment_avg_confidence(seg, frame_probs)
            if conf < 0.65 and (seg["end"] - seg["start"]) >= 3.0:
                low_confidence_segs.append((seg["start"], seg["end"], conf))
        low_confidence_segs.sort(key=lambda s: s[2])

        speech_duration = sum(seg["end"] - seg["start"] for seg in speech_ts)
        silence_duration = total_duration - speech_duration
        silence_ratio = silence_duration / total_duration * 100

        gaps = find_silence_gaps(speech_ts, total_duration)
        long_gaps = [(s, e, e - s) for s, e in gaps if (e - s) >= MIN_SILENCE_SEC]
        long_gaps.sort(key=lambda g: g[2], reverse=True)

        results.append(
            {
                "file": fname,
                "total": total_duration,
                "speech": speech_duration,
                "silence": silence_duration,
                "silence_ratio": silence_ratio,
                "long_gaps": long_gaps,
                "num_speech_segments": len(speech_ts),
                "low_confidence_segs": low_confidence_segs,
            }
        )

    os.remove(os.path.join(tmpdir, "tmp.wav")) if os.path.exists(os.path.join(tmpdir, "tmp.wav")) else None
    os.rmdir(tmpdir)

    # ---- 표 출력 ----
    print()
    print(f"{'파일':38s} {'전체(초)':>9s} {'발화(초)':>9s} {'무음(초)':>9s} {'무음%':>7s} {'10s+구간수':>10s}")
    print("-" * 95)
    for r in results:
        print(
            f"{r['file']:38s} {r['total']:9.1f} {r['speech']:9.1f} {r['silence']:9.1f} "
            f"{r['silence_ratio']:6.1f}% {len(r['long_gaps']):10d}"
        )

    print()
    print("=== 10초 이상 무음 구간 상세 (파일당 전체) ===")
    for r in results:
        print(f"\n[{r['file']}]")
        if not r["long_gaps"]:
            print("  10초 이상 무음 구간 없음")
            continue
        for start, end, dur in r["long_gaps"]:
            print(f"  {fmt_mmss(start)} ~ {fmt_mmss(end)}  ({dur:.1f}초)")

    print()
    print("=== 승원 직접 청취용 타임스탬프 (파일당 상위 2~3개, 긴 순) ===")
    for r in results:
        print(f"\n[{r['file']}]")
        top = r["long_gaps"][:3]
        if not top:
            print("  (10초 이상 무음 구간 없음)")
            continue
        for start, end, dur in top:
            print(f"  -> {fmt_mmss(start)}부터 재생해서 확인 (감지된 무음 길이 {dur:.1f}초, {fmt_mmss(start)}~{fmt_mmss(end)})")

    print()
    print("=== 오판(배경소음 -> 발화) 의심 구간 — 3초 이상, 평균확신도 0.65 미만 ===")
    print("(threshold=0.5 근처일수록 애매한 판정. 100% 확정은 아니므로 직접 들어봐야 함)")
    any_low_conf = False
    for r in results:
        if not r["low_confidence_segs"]:
            continue
        any_low_conf = True
        print(f"\n[{r['file']}]")
        for start, end, conf in r["low_confidence_segs"]:
            print(f"  {fmt_mmss(start)} ~ {fmt_mmss(end)}  (평균확신도 {conf:.2f})")
    if not any_low_conf:
        print("  해당 구간 없음 (모든 발화 구간이 확신도 0.65 이상)")

    # ---- 전체 절감률 계산 ----
    total_all = sum(r["total"] for r in results)
    silence_all = sum(r["silence"] for r in results)
    overall_ratio = silence_all / total_all * 100 if total_all else 0
    saved_won = silence_all * WON_PER_SEC

    print()
    print("=== 전체 예상 절감률 ===")
    print(f"전체 재생시간 합계: {total_all:.1f}초 ({total_all/60:.1f}분)")
    print(f"무음으로 감지된 시간 합계: {silence_all:.1f}초 ({silence_all/60:.1f}분)")
    print(f"전체 예상 절감률: {overall_ratio:.1f}%")
    print(f"초당 단가 {WON_PER_SEC:.4f}원 기준, 예상 절감액: {saved_won:.1f}원")


if __name__ == "__main__":
    sys.exit(main())
