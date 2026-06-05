from __future__ import annotations

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
    """
    세션 추가. 초과 시 False 반환 (로그인 차단)
    """
    if _redis is None:
        return True

    limit = TIER_SESSION_LIMITS.get(tier, 1)
    session_key = f"sessions:{hospital_id}"

    # 현재 활성 세션 수 확인
    current = _redis.llen(session_key)
    if current >= limit:
        return False  # 세션 초과 → 로그인 차단

    # 세션 추가
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
