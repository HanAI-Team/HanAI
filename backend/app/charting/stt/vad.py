# app/charting/stt/vad.py
"""CLOVA Speech로 보내기 전, 10초 이상 연속되는 무음 구간을 잘라내는 전처리.

원본 파일은 절대 건드리지 않는다 — 임시 파일만 만들어서 처리하고, 실패하면
무조건 원본 audio_bytes를 그대로 반환한다. 이 트리밍은 비용을 줄이기 위한
최적화일 뿐이므로, 실패가 STT 자체를 막아서는 안 된다.
"""
import logging
import os
import struct
import subprocess
import tempfile

import torch
from silero_vad import get_speech_timestamps, load_silero_vad

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
MIN_SILENCE_SEC = 10.0  # 이보다 짧은 무음은 자연스러운 대화 텀으로 보고 자르지 않음
PAD_SEC = 0.75  # 무음 구간 경계에서 이만큼은 남기고 자름 (단어 잘림 방지)

_model = None


def _get_model():
    global _model
    if _model is None:
        _model = load_silero_vad()
    return _model


def _decode_to_wav(src_path: str, dst_path: str) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", src_path,
            "-ac", "1", "-ar", str(SAMPLE_RATE), "-c:a", "pcm_s16le", "-f", "wav",
            dst_path,
        ],
        check=True, capture_output=True,
    )


def _read_wav_pcm(wav_path: str) -> torch.Tensor:
    """RIFF/data 청크를 직접 파싱한다 (WAVE_FORMAT_EXTENSIBLE 등 표준 `wave` 모듈이
    못 읽는 헤더도 안전하게 처리하기 위함 — validate_vad.py 검증 스크립트와 동일한 방식)."""
    with open(wav_path, "rb") as f:
        data = f.read()
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ValueError("올바른 WAV 파일이 아닙니다")
    pos = 12
    pcm_bytes = None
    while pos + 8 <= len(data):
        chunk_id = data[pos:pos + 4]
        chunk_size = struct.unpack("<I", data[pos + 4:pos + 8])[0]
        chunk_start = pos + 8
        if chunk_id == b"data":
            pcm_bytes = data[chunk_start:chunk_start + chunk_size]
            break
        pos = chunk_start + chunk_size + (chunk_size % 2)
    if pcm_bytes is None:
        raise ValueError("WAV data 청크를 찾을 수 없습니다")
    samples = torch.frombuffer(bytearray(pcm_bytes), dtype=torch.int16)
    return samples.float() / 32768.0


def _compute_keep_ranges(speech_segments: list[dict], total_duration: float) -> list[tuple[float, float]]:
    """10초 이상 연속 무음 구간만 제거 대상으로 삼아, 남길 구간(keep ranges)을 계산한다.
    각 제거 구간 경계에는 PAD_SEC만큼 여유를 남긴다."""
    gaps = []
    cursor = 0.0
    for seg in speech_segments:
        if seg["start"] - cursor > 0:
            gaps.append((cursor, seg["start"]))
        cursor = seg["end"]
    if total_duration - cursor > 0:
        gaps.append((cursor, total_duration))

    long_gaps = [(s, e) for s, e in gaps if (e - s) >= MIN_SILENCE_SEC]

    keep_ranges = []
    cursor = 0.0
    for gap_start, gap_end in long_gaps:
        cut_start = gap_start + PAD_SEC
        cut_end = gap_end - PAD_SEC
        if cut_end <= cut_start:
            continue
        keep_ranges.append((cursor, cut_start))
        cursor = cut_end
    keep_ranges.append((cursor, total_duration))
    return [(s, e) for s, e in keep_ranges if e > s]


def _cut_and_concat(src_path: str, keep_ranges: list[tuple[float, float]], dst_path: str) -> None:
    filter_parts = []
    concat_inputs = []
    for i, (start, end) in enumerate(keep_ranges):
        filter_parts.append(f"[0:a]atrim=start={start:.3f}:end={end:.3f},asetpts=PTS-STARTPTS[a{i}]")
        concat_inputs.append(f"[a{i}]")
    filter_complex = (
        ";".join(filter_parts) + ";" + "".join(concat_inputs) + f"concat=n={len(keep_ranges)}:v=0:a=1[out]"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-i", src_path, "-filter_complex", filter_complex, "-map", "[out]", dst_path],
        check=True, capture_output=True,
    )


def trim_silence(audio_bytes: bytes, ext: str = "mp3") -> bytes:
    """10초 이상 연속 무음 구간을 제거한 오디오 바이트를 반환한다.

    실패하거나 자를 무음 구간이 없으면 원본 audio_bytes를 그대로 반환한다.
    """
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            src_path = os.path.join(tmpdir, f"input.{ext}")
            with open(src_path, "wb") as f:
                f.write(audio_bytes)

            wav_path = os.path.join(tmpdir, "input.wav")
            _decode_to_wav(src_path, wav_path)
            audio = _read_wav_pcm(wav_path)
            total_duration = len(audio) / SAMPLE_RATE

            speech_ts = get_speech_timestamps(
                audio,
                _get_model(),
                sampling_rate=SAMPLE_RATE,
                min_silence_duration_ms=100,
                return_seconds=True,
            )
            keep_ranges = _compute_keep_ranges(speech_ts, total_duration)

            if len(keep_ranges) <= 1:
                logger.info("[VAD] 10초 이상 무음 구간 없음 — 원본 그대로 전송")
                return audio_bytes

            trimmed_path = os.path.join(tmpdir, f"trimmed.{ext}")
            _cut_and_concat(src_path, keep_ranges, trimmed_path)

            with open(trimmed_path, "rb") as f:
                trimmed_bytes = f.read()

            kept_duration = sum(e - s for s, e in keep_ranges)
            logger.info(
                f"[VAD] 무음 트리밍 완료 — {total_duration:.1f}s -> {kept_duration:.1f}s "
                f"({total_duration - kept_duration:.1f}s 제거, {len(keep_ranges)}개 구간 유지)"
            )
            return trimmed_bytes

    except Exception as e:
        logger.warning(f"[VAD] 무음 트리밍 실패, 원본 오디오 사용: {e}")
        return audio_bytes
