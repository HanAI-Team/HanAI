from __future__ import annotations

import json

from app.core.config import settings

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


def set_verify_pending(callback_id: str, data: dict, ttl: int = 300) -> None:
    if _redis is None:
        return
    _redis.set(f"verify:{callback_id}", json.dumps(data), ex=ttl)


def get_verify_pending(callback_id: str) -> dict | None:
    if _redis is None:
        return None
    raw = _redis.get(f"verify:{callback_id}")
    if raw is None:
        return None
    return json.loads(raw)


def del_verify_pending(callback_id: str) -> None:
    if _redis is None:
        return
    _redis.delete(f"verify:{callback_id}")
