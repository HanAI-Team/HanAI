import requests
import pandas as pd
import os

def collect_public_data():
    """
    공공데이터포털 한의학 데이터 수집
    data.go.kr 에서 한의학 관련 공개 데이터
    """
    
    # 저장 폴더 만들기
    os.makedirs('data/raw', exist_ok=True)
    
    # 1. 한국한의학연구원 표준처방 데이터
    print("공공데이터 수집 중...")
    
    urls = [
        "https://www.kiom.re.kr",  # 한국한의학연구원
        "https://nikom.or.kr",     # 국립한의학연구원
    ]
    
    print("수집 가능한 공공 한의학 데이터 목록:")
    print("1. 한국한의학연구원 표준처방 DB")
    print("2. 건강보험심사평가원 한약 처방 통계")
    print("3. 국가생약정보 DB")
    
    return urls

if __name__ == "__main__":
    collect_public_data()