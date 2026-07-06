from __future__ import annotations

import json

from app.core.config import settings
from app.core.crypto import decrypt, encrypt

TIER_SESSION_LIMITS = {
    "basic": 1,
    "standard": 3,
    "premium": 5,
}


def get_redis():
    if not settings.UPSTASH_REDIS_URL or not settings.UPSTASH_REDIS_TOKEN:
        return None
    from upstash_redis import Redis

    return Redis(url=settings.UPSTASH_REDIS_URL, token=settings.UPSTASH_REDIS_TOKEN)


_redis = get_redis()


async def add_token_blacklist(token: str, expire_seconds: int) -> None:
    if _redis is None:
        return
    _redis.set(f"blacklist:{token}", 1, ex=expire_seconds)


async def is_token_blacklisted(token: str) -> bool:
    if _redis is None:
        return False
    return _redis.exists(f"blacklist:{token}") == 1


# import asyncio
# count = await asyncio.to_thread(_redis.incr, full_key) 추후 트래픽 많아지면 수정하기
async def check_rate_limit(key: str, limit: int, window_seconds: int) -> bool:
    if _redis is None:
        return True
    full_key = f"ratelimit:{key}"
    count = _redis.incr(full_key)
    if count == 1:
        _redis.expire(full_key, window_seconds)
    return count <= limit


async def add_session(
    hospital_id: str, token: str, tier: str, expire_seconds: int
) -> bool:
    if _redis is None:
        return True
    limit = TIER_SESSION_LIMITS.get(tier, 1)
    session_key = f"sessions:{hospital_id}"

    current = _redis.llen(session_key)
    if current >= limit:
        # 차단 대신 가장 오래된 세션 제거
        _redis.lpop(session_key)

    _redis.rpush(session_key, token)
    _redis.expire(session_key, expire_seconds)
    return True


async def remove_session(hospital_id: str, token: str) -> None:
    """
    로그아웃 시 세션 제거
    """
    if _redis is None:
        return
    session_key = f"sessions:{hospital_id}"
    _redis.lrem(session_key, 0, token)


# jumin(주민번호)·password는 콜백 대기 중(최대 TTL) Redis에 평문으로 남으면 안 되는 값이라
# Patient.rrn과 동일한 AES-256-GCM 함수(app.core.crypto)로 필드 단위 암호화한다.
_VERIFY_PENDING_SENSITIVE_FIELDS = ("jumin", "password")


class VerifyPendingDecryptionError(Exception):
    """pending 데이터의 민감 필드 복호화 실패(키 불일치·데이터 변조 등).
    호출부가 "데이터 없음"과 구분해서 처리해야 하므로 None으로 뭉개지 않고 예외로 알린다."""


def set_verify_pending(callback_id: str, data: dict, ttl: int = 300) -> None:
    if _redis is None:
        return
    payload = dict(data)
    for field in _VERIFY_PENDING_SENSITIVE_FIELDS:
        if payload.get(field) is not None:
            payload[field] = encrypt(payload[field])
    _redis.set(f"verify:{callback_id}", json.dumps(payload), ex=ttl)


def get_verify_pending(callback_id: str) -> dict | None:
    """pending 데이터가 없으면(미저장/TTL 만료) None을 반환한다.
    데이터는 있는데 민감 필드 복호화에 실패하면 VerifyPendingDecryptionError를 던진다
    (키 불일치·변조 상황을 "못 찾음"과 같은 취급으로 조용히 넘기지 않기 위함)."""
    if _redis is None:
        return None
    raw = _redis.get(f"verify:{callback_id}")
    if raw is None:
        return None

    payload = json.loads(raw)
    for field in _VERIFY_PENDING_SENSITIVE_FIELDS:
        if payload.get(field) is None:
            continue
        try:
            payload[field] = decrypt(payload[field])
        except Exception as exc:
            raise VerifyPendingDecryptionError(
                f"pending 데이터 복호화 실패: callback_id={callback_id}, field={field}"
            ) from exc
    return payload


def del_verify_pending(callback_id: str) -> None:
    if _redis is None:
        return
    _redis.delete(f"verify:{callback_id}")
