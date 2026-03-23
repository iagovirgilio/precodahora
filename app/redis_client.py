import logging

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger("precodahora.api")

_pool: aioredis.Redis | None = None


async def init_redis() -> None:
    global _pool
    url = settings.redis_url.strip()
    if not url:
        return
    _pool = aioredis.from_url(
        url,
        encoding="utf-8",
        decode_responses=True,
    )
    try:
        await _pool.ping()
        logger.info("redis_connected")
    except Exception:
        logger.exception("redis_connect_failed_on_startup")
        await _pool.aclose()
        _pool = None


async def close_redis() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None
        logger.info("redis_closed")


def get_async_redis() -> aioredis.Redis | None:
    return _pool


async def redis_ready() -> tuple[bool, str]:
    if not settings.redis_url.strip():
        return True, "skipped"
    client = get_async_redis()
    if client is None:
        return False, "unavailable"
    try:
        if await client.ping():
            return True, "ok"
        return False, "ping_failed"
    except Exception:
        logger.exception("redis_ready_ping_failed")
        return False, "error"
