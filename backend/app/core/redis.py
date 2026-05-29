from __future__ import annotations

from app.core.config import settings


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
