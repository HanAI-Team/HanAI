# HanAI 프로젝트 컨텍스트 v3

> 최종 업데이트: 2026-07-02  
> 서비스명: Zinmac (한의원 AI 진료 보조 + 청구 SW)  
> HIRA 청구소프트웨어 기능검사 대응 포함

---

## 프로젝트 개요

한의원 대상 SaaS. 핵심 기능:
- AI 진단 보조 (음성 → 사상체질/처방 분석)
- 건강보험 청구 (EDI 생성, 요양급여비용 산정)
- HIRA 청구소프트웨어 기능검사 보안 요건 대응

---

## 완료된 작업

### HIRA 보안 부문 (Task 1~6)

| # | 항목 | 구현 내용 |
|---|------|----------|
| 1 | DB 마이그레이션 | `login_logs`, `account_histories`, `password_histories` 테이블 추가 |
| 2 | 비밀번호 정책 | 복잡도 검증(8자+영문+숫자+특수문자), 재사용 금지(최근 5개), 90일 만료 |
| 3 | 로그인 로그 | 성공/실패 IP·시각 DB 저장 (`login_logs`) |
| 4 | 계정 이력 | 생성/비활성화/역할변경 → `account_histories` 기록 |
| 5 | 조회 API | `GET /auth/login-logs`, `GET /auth/account-histories` (owner 전용) |
| 6 | 세션 타임아웃 | 프론트 30분 idle 자동 로그아웃 (`useIdleLogout`) |

### 접속기록 범위 확장
- 환자 조회 / 진료기록 조회 시 READ audit log 추가
- PR #326

### 개인정보 파기 기능
- `PATCH /api/patients/{id}/anonymize`
- 이름·주민번호·전화번호 → 익명화 처리
- PR #701956b

### 착오청구 예방 — KCD 검증
- 성별 제한 상병코드 청구 차단 (남성 전용/여성 전용)
- 법정감염병 여부 반환
- PR #324

### 차등수가 graduated_fee_index 검증
- 범위 0 이상 1 이하 검증 추가
- PR #329

### kmishe_writer.py deprecated
- EDI 폐지 (2026-04-24) 대응
- KMISHE EDIFACT 생성기 비활성화
- PR #317

### 접근관리 화면 UI
- settings 페이지에 로그인 기록 / 계정 이력 조회 UI 추가
- PR #318

### 처방전/영수증 PDF 출력
- 청구 화면에서 처방전·영수증 PDF 생성 및 인쇄

### KCD U코드 137개 시딩
- COVID-19 등 U코드 상병 시드 데이터 추가

### 환자 주민번호 AES-256-GCM 암호화
- `core/crypto.py` — `rrn` 컬럼 암호화 적용

### hospitals.institution_code 추가
- 요양기관기호 컬럼 추가

### 스플래시 애니메이션
- 웹 / 앱 초기 로딩 스플래시 화면 추가

---

## 남은 작업

| 항목 | 담당 | 비고 |
|------|------|------|
| 월 청구 건수 제한 (베이직 50건) | 태균 | 현재 브랜치: `feat/ytk-claim-limit` |
| SaturdayHolidayStaffing 모델 추가 | 승희 | MT050 특정내역 대응 |
| 포털 SAM FILE 구조 확인 | 승희 | — |
| 결제 시스템 (포트원) | — | HIRA 기능검사 인증 이후 착수 |
| AWS 이전 | — | Vercel → AWS (시점 미정) |

---

## 기술 스택

```
backend/   FastAPI + SQLAlchemy (AsyncSession) + Alembic + PostgreSQL
frontend/  Next.js (TypeScript) + Vercel
mobile/    React Native (Expo)
```

---

## 주요 파일 위치

```
backend/app/
├── auth/
│   ├── router.py      로그인·로그아웃·비밀번호 변경·로그/이력 조회 API
│   ├── service.py     인증 서비스 (비밀번호 검증·이력·계정이력 기록)
│   └── schema.py      LoginRequest, RegisterRequest, ChangePasswordRequest
├── core/
│   ├── models.py      Doctor, StaffAccount, Hospital, LoginLog, AccountHistory, PasswordHistory
│   ├── deps.py        get_current_user, get_current_doctor (세션 만료·강제변경 체크 포함)
│   ├── audit.py       write_audit() 헬퍼
│   └── crypto.py      AES-256-GCM (주민번호 암호화)
├── billing/           청구 엔진 (EDI 생성, 본인부담금 산정)
├── patients/          환자 관리 (anonymize 포함)
└── kcd/               KCD 검증 (성별·감염병·U코드)
```

---

## 보안 항목 최종 상태

| # | HIRA 항목 | 상태 |
|---|-----------|:----:|
| 1 | 사용자 인증 (JWT) | ✅ |
| 2 | 계정 발급 이력 (시작/종료일) | ✅ |
| 3 | 권한 부여 (최소권한·말소·3년보관) | ✅ |
| 4 | 비밀번호 작성규칙 (조합·길이) | ✅ |
| 5 | 비밀번호 암호화 (bcrypt) | ✅ |
| 6 | 비밀번호 주기 변경 (90일) | ✅ |
| 7 | 비밀번호 재설정 후 강제변경 | ✅ |
| 8 | 비밀번호 이력 재사용 금지 | ✅ |
| 9 | 접근 제한 (5회 실패 잠금) | ✅ |
| 10 | 사용자 재인증 (세션 타임아웃) | ✅ |
| 11 | 접근관리 화면 | ✅ |
| 12 | 로그인 성공·실패 로그 (IP·시각) | ✅ |
| 13 | 개인정보 암호화 (AES-256) | ✅ |
| 14 | 암호화 알고리즘 (권고) | ✅ |
