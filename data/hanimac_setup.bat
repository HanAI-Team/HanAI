@echo off
chcp 65001 > nul
echo.
echo ========================================
echo  한의맥 → Zinmac 동기화 에이전트 설치
echo ========================================
echo.

:: Python 확인
python --version > nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo https://www.python.org 에서 Python 3.11 이상을 설치하세요.
    pause
    exit /b 1
)

:: 의존성 설치
echo [1/3] 필요 패키지 설치 중...
pip install pyodbc requests -q
if errorlevel 1 (
    echo [오류] 패키지 설치 실패
    pause
    exit /b 1
)
echo       완료

:: 첫 실행 (전체 이전)
echo.
echo [2/3] 한의맥 환자 데이터 초기 이전 중...
echo       (처음 실행 시 면허번호와 비밀번호를 입력하세요)
echo.
python "%~dp0hanimac_sync_agent.py"
if errorlevel 1 (
    echo [오류] 초기 이전 실패 — 오류 내용을 확인하세요.
    pause
    exit /b 1
)

:: 작업 스케줄러 등록 (1시간마다 자동 실행)
echo.
echo [3/3] Windows 작업 스케줄러 등록 중... (1시간마다 자동 실행)
schtasks /create /tn "ZinmacHanimacSync" /tr "python \"%~dp0hanimac_sync_agent.py\"" /sc hourly /f > nul
if errorlevel 1 (
    echo [경고] 작업 스케줄러 등록 실패 — 관리자 권한으로 다시 실행하세요.
) else (
    echo       완료 — 매 시간 자동으로 동기화됩니다.
)

echo.
echo ========================================
echo  설치 완료!
echo  이후 환자 추가 시 1시간 이내 자동 반영
echo ========================================
echo.
pause
