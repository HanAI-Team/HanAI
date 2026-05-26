import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'api'))

import whisper
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import tempfile
from models.diagnosis import diagnose
from api.patient import add_record

model = whisper.load_model("base")

def record_audio(duration=60, samplerate=16000):
    print(f"녹음 시작... ({duration}초)")
    audio = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype='float32')
    sd.wait()
    print("녹음 완료!")
    return audio, samplerate

def transcribe_audio(audio, samplerate):
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        wav.write(f.name, samplerate, (audio * 32767).astype(np.int16))
        result = model.transcribe(f.name, language='ko')
        os.unlink(f.name)
    return result['text']

def record_and_transcribe(duration=60):
    audio, samplerate = record_audio(duration)
    text = transcribe_audio(audio, samplerate)
    return text

def auto_chart(patient_id, duration=60):
    text = record_and_transcribe(duration)
    print(f"\n[인식된 텍스트]\n{text}")
    
    print("\n분석 중...")
    result = diagnose(text)
    print(f"\n[진단 결과]\n{result}")
    
    add_record(
        patient_id=patient_id,
        symptoms=text,
        diagnosis=result,
        prescription="처방 자동 추출 예정"
    )
    print("\n차트 자동 저장 완료!")
    return result