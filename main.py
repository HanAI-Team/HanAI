from models.diagnosis import diagnose
from models.recorder import record_and_transcribe, auto_chart

def main():
    print("=== HanAI ===")
    print("1. 증상 직접 입력")
    print("2. 음성 녹음으로 입력")
    print("3. 오토 차팅 (녹음 → 자동 차트 저장)")

    choice = input("\n선택하세요 (1/2/3): ")

    if choice == "1":
        symptoms = input("환자 증상을 입력하세요: ")
        result = diagnose(symptoms)
        print(f"\n[진단 결과]\n{result}")

    elif choice == "2":
        seconds = input("녹음 시간 (초, 기본 60): ")
        duration = int(seconds) if seconds else 60
        symptoms = record_and_transcribe(duration)
        print(f"\n[인식된 텍스트]\n{symptoms}")
        result = diagnose(symptoms)
        print(f"\n[진단 결과]\n{result}")

    elif choice == "3":
        patient_id = input("환자 ID를 입력하세요: ")
        seconds = input("녹음 시간 (초, 기본 60): ")
        duration = int(seconds) if seconds else 60
        auto_chart(int(patient_id), duration)

    else:
        print("잘못된 입력입니다.")

if __name__ == "__main__":
    main()