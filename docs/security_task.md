# 청구SW 기능검사 — 보안 부문 구현 태스크

> HIRA 청구소프트웨어 기능검사 보안 부문 19종 기준  
> 담당자가 이 문서 하나로 처음부터 구현할 수 있도록 작성함

---

## 현재 상태 요약

| # | 항목 | 상태 | 비고 |
|---|------|:----:|------|
| 1 | 사용자 인증 | ✅ | JWT Bearer, `auth/router.py` |
| 2 | 계정 발급 이력 (시작/종료일) | ❌ | 테이블 없음 |
| 3 | 권한 부여 (최소권한·말소·3년보관) | ❌ | role 필드만 있음 |
| 4 | 비밀번호 작성규칙 (조합·길이) | ❌ | 검증 없음 |
| 5 | 비밀번호 암호화 | ✅ | bcrypt (`auth/service.py:10`) |
| 6 | 비밀번호 주기 변경 (90일) | ❌ | `password_changed_at` 필드 없음 |
| 7 | 비밀번호 재설정 후 강제변경 | ❌ | reset API는 있으나 강제플래그 없음 |
| 8 | 비밀번호 이력 재사용 금지 | ❌ | 이력 테이블 없음 |
| 9 | 접근 제한 (5회 실패 잠금) | ✅ | Redis 기반, `auth/router.py:149-178` |
| 10 | 사용자 재인증 (세션타임아웃) | ❌ | JWT exp는 있으나 idle timeout 없음 |
| 11 | 접근관리 화면 | ❌ | 관리 API/UI 없음 |
| 12 | 로그인 성공·실패 로그 (IP·시각) | ❌ | Redis 카운팅만 있고 DB 저장 없음 |
| 13 | 개인정보 암호화 | ✅ | `rrn` AES (`core/crypto.py`) |
| 14 | 암호화 알고리즘 (권고) | ✅ | AES-256 |

---

## 코드베이스 구조 (관련 파일만)

```
backend/
├── app/
│   ├── auth/
│   │   ├── router.py      ← 로그인·로그아웃·비밀번호 변경 엔드포인트
│   │   ├── service.py     ← register_doctor, create_access_token
│   │   └── schema.py      ← LoginRequest, RegisterRequest, ChangePasswordRequest
│   ├── core/
│   │   ├── models.py      ← Doctor, StaffAccount, Hospital (DB 모델)
│   │   ├── deps.py        ← get_current_user, get_current_doctor (인증 미들웨어)
│   │   ├── audit.py       ← write_audit() (AuditLog 기록 헬퍼)
│   │   └── redis.py       ← 세션·토큰 블랙리스트·레이트리밋
│   └── hospitals/
│       └── router.py      ← 병원 정보 관리
└── alembic/versions/      ← DB 마이그레이션 파일
```

---

## Task 1 — DB 마이그레이션 (3개 파일)

### 1-1. `account_histories` + `login_logs` 테이블

```
파일명: alembic/versions/XXXX_add_account_history_and_login_log.py
```

```python
# account_histories
# 계정 생성·비활성화·역할 변경 이력 (3년 보관)
id          UUID  PK
account_type  String  # "doctor" | "staff"
account_id    UUID    # Doctor.id 또는 StaffAccount.id
action        String  # "created" | "deactivated" | "role_changed"
actor_id      UUID    # 처리한 주체 (관리자 ID)
started_at    DateTime
ended_at      DateTime nullable  # 계정 종료일 (비활성화 시 채워짐)
detail        Text nullable      # 역할변경 시 before→after 등

# login_logs
# 로그인 성공/실패 영구 기록 (HIRA: 접속기록 보관)
id            UUID  PK
account_type  String   # "doctor" | "staff"
account_id    UUID nullable  # 계정 없는 시도는 None
success       Boolean
ip_address    String(45)  # IPv6 대비
user_agent    String(500) nullable
attempted_at  DateTime
```

### 1-2. 비밀번호 정책 컬럼 + 이력 테이블

```
파일명: alembic/versions/XXXX_add_password_policy.py
```

```python
# doctors 테이블에 컬럼 추가
ALTER TABLE doctors ADD COLUMN password_changed_at  DateTime nullable
ALTER TABLE doctors ADD COLUMN force_password_change Boolean DEFAULT false

# staff_accounts 테이블에 컬럼 추가
ALTER TABLE staff_accounts ADD COLUMN password_changed_at  DateTime nullable
ALTER TABLE staff_accounts ADD COLUMN force_password_change Boolean DEFAULT false

# password_histories (재사용 금지용, 최근 5개 유지)
id            UUID  PK
account_type  String
account_id    UUID
password_hash String
created_at    DateTime
```

---

## Task 2 — 비밀번호 정책 (`auth/service.py`)

### 2-1. 복잡도 검증 함수 추가

**HIRA 기준: 8자 이상, 영문·숫자·특수문자 각 1자 이상**

```python
# auth/service.py 에 추가
import re

def validate_password_complexity(password: str) -> list[str]:
    """
    반환값: 위반 메시지 목록. 빈 리스트면 통과.
    HIRA 기준: 8자 이상, 영문+숫자+특수문자 조합
    """
    errors = []
    if len(password) < 8:
        errors.append("비밀번호는 8자 이상이어야 합니다.")
    if not re.search(r"[A-Za-z]", password):
        errors.append("영문자를 포함해야 합니다.")
    if not re.search(r"\d", password):
        errors.append("숫자를 포함해야 합니다.")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{}|;:',.<>?/~`]", password):
        errors.append("특수문자를 포함해야 합니다.")
    return errors
```

### 2-2. RegisterRequest / ChangePasswordRequest 에 검증 연결

```python
# auth/schema.py
class RegisterRequest(BaseModel):
    ...
    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        from app.auth.service import validate_password_complexity
        errors = validate_password_complexity(v)
        if errors:
            raise ValueError(" / ".join(errors))
        return v

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def new_password_complexity(cls, v: str) -> str:
        from app.auth.service import validate_password_complexity
        errors = validate_password_complexity(v)
        if errors:
            raise ValueError(" / ".join(errors))
        return v
```

### 2-3. 비밀번호 이력 저장 + 재사용 금지

```python
# auth/service.py 의 change_password 로직에 추가
# (현재는 router.py 인라인 처리됨 → service.py 함수로 분리 권장)

async def check_password_history(
    db: AsyncSession,
    account_type: str,
    account_id: UUID,
    new_password: str,
    limit: int = 5,
) -> bool:
    """최근 limit개 이력과 겹치면 True(재사용) 반환."""
    from app.core.models import PasswordHistory
    result = await db.execute(
        select(PasswordHistory)
        .where(
            PasswordHistory.account_type == account_type,
            PasswordHistory.account_id == account_id,
        )
        .order_by(PasswordHistory.created_at.desc())
        .limit(limit)
    )
    histories = result.scalars().all()
    return any(pwd_context.verify(new_password, h.password_hash) for h in histories)

async def save_password_history(
    db: AsyncSession, account_type: str, account_id: UUID, password_hash: str
) -> None:
    from app.core.models import PasswordHistory
    db.add(PasswordHistory(
        account_type=account_type,
        account_id=account_id,
        password_hash=password_hash,
    ))
```

---

## Task 3 — 로그인 로직 수정 (`auth/router.py`)

### 3-1. 로그인 성공·실패 → `login_logs` DB 기록

```python
# router.py 의 login() / staff_login() 에 추가
# Request 객체에서 IP 추출하려면 파라미터에 request: Request 추가

from fastapi import Request
from app.core.models import LoginLog

@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    request: Request,           # ← 추가
    db: AsyncSession = Depends(get_db),
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    
    # ... 기존 인증 로직 ...
    
    # 실패 시:
    db.add(LoginLog(
        account_type="doctor",
        account_id=doctor.id,  # 계정 찾은 경우
        success=False,
        ip_address=ip,
        user_agent=ua,
    ))
    await db.commit()
    
    # 성공 시:
    db.add(LoginLog(
        account_type="doctor",
        account_id=doctor.id,
        success=True,
        ip_address=ip,
        user_agent=ua,
    ))
    await db.commit()
```

### 3-2. 비밀번호 만료 체크 (90일)

```python
# core/deps.py 의 get_current_doctor / get_current_user 에 추가
from datetime import timedelta

PW_EXPIRE_DAYS = 90

def _is_password_expired(changed_at) -> bool:
    if changed_at is None:
        return False  # 최초 설정 전이면 패스 (또는 True로 바꿔 강제)
    return datetime.now(timezone.utc) - changed_at > timedelta(days=PW_EXPIRE_DAYS)
```

`get_current_doctor` 안에서 doctor 조회 후:
```python
if _is_password_expired(doctor.password_changed_at):
    raise HTTPException(
        status_code=403,
        detail="비밀번호 사용 기간(90일)이 만료되었습니다. 변경 후 이용하세요.",
        headers={"X-Require": "password-change"},
    )
if doctor.force_password_change:
    raise HTTPException(
        status_code=403,
        detail="초기 비밀번호를 변경해야 합니다.",
        headers={"X-Require": "password-change"},
    )
```

### 3-3. 관리자 비밀번호 리셋 → 강제변경 플래그 설정

```python
# router.py 의 reset_password 수정
doctor.password_hash = service.pwd_context.hash(temp_password)
doctor.force_password_change = True   # ← 추가
doctor.password_changed_at = None     # ← 추가 (만료 타이머 리셋)
await db.commit()
```

### 3-4. 비밀번호 변경 성공 시 플래그 해제

```python
# router.py 의 change_password 수정
doctor.password_hash = service.pwd_context.hash(data.new_password)
doctor.password_changed_at = datetime.now(timezone.utc)  # ← 추가
doctor.force_password_change = False                      # ← 추가
await db.commit()
```

---

## Task 4 — 계정 이력 기록 (`auth/service.py`)

계정 생성·비활성화 시 `account_histories`에 기록.

```python
async def record_account_history(
    db: AsyncSession,
    account_type: str,
    account_id: UUID,
    action: str,        # "created" | "deactivated" | "role_changed"
    actor_id: UUID | None = None,
    detail: str | None = None,
) -> None:
    from app.core.models import AccountHistory
    db.add(AccountHistory(
        account_type=account_type,
        account_id=account_id,
        action=action,
        actor_id=actor_id,
        started_at=datetime.now(timezone.utc),
        detail=detail,
    ))
```

호출 위치:
- `register_doctor()` 완료 후 → `action="created"`
- StaffAccount 생성 후 → `action="created"`
- `is_active = False` 처리 후 → `action="deactivated"`
- role 변경 후 → `action="role_changed"`

---

## Task 5 — 조회 API (`auth/router.py`)

```
GET /auth/login-logs
  - owner 전용
  - query: start_date, end_date, success (bool)
  - 응답: [{account_type, account_id, success, ip_address, attempted_at}, ...]

GET /auth/account-histories
  - owner 전용
  - 응답: [{account_type, account_id, action, started_at, ended_at, detail}, ...]
```

---

## Task 6 — 세션 타임아웃 (프론트엔드)

백엔드는 JWT 만료로 충분. 프론트에서 처리.

```
frontend/lib/api/client.ts (또는 axios interceptor):
  - 401 응답 수신 시 → localStorage 토큰 삭제 → /login 리다이렉트
  - 추가로 idle 감지 (30분 마우스·키보드 없으면 자동 로그아웃) 원하면 별도 훅 추가
```

```typescript
// 예시: useIdleLogout.ts
// 30분 idle 후 logout() 호출
```

---

## 구현 순서 (권장)

```
Day 1: Task 1 (마이그레이션 3개)
Day 2: Task 2 (비밀번호 정책 — 복잡도·이력·만료)
Day 3: Task 3 (로그인 로직 — 로그 기록·강제변경)
Day 4: Task 4 + 5 (계정이력 기록 + 조회 API)
Day 5: Task 6 (프론트 세션타임아웃) + 테스트 작성
```

---

## 테스트 체크리스트

구현 완료 후 아래를 직접 확인:

- [ ] 8자 미만 비밀번호로 회원가입 → 400 에러
- [ ] 특수문자 없는 비밀번호 → 400 에러
- [ ] 로그인 5회 실패 → 403 잠금 (이미 동작, 회귀 확인)
- [ ] 비밀번호 변경 후 `password_changed_at` DB 업데이트 확인
- [ ] admin reset 후 로그인 → 403 + X-Require: password-change
- [ ] 최근 5개 비밀번호 재사용 시도 → 400 에러
- [ ] 로그인 성공·실패 모두 `login_logs` 테이블에 IP 포함 저장 확인
- [ ] `GET /auth/login-logs` → owner만 접근, 다른 role은 403
- [ ] 계정 생성 시 `account_histories` 에 created 이력 확인
