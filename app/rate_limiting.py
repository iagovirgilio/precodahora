import logging
import time
import uuid
from collections import defaultdict, deque

import redis.asyncio as aioredis

from app.config import settings
from app.redis_client import get_async_redis

logger = logging.getLogger("precodahora.api")

_memory_buckets: dict[str, deque[float]] = defaultdict(deque)

_SLIDING_WINDOW_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]
redis.call('ZREMRANGEBYSCORE', key, '-inf', now - window)
local c = redis.call('ZCARD', key)
if c >= limit then
  return 0
end
redis.call('ZADD', key, now, member)
redis.call('EXPIRE', key, math.ceil(window) + 5)
return 1
"""


def clear_memory_buckets() -> None:
    _memory_buckets.clear()


def memory_try_consume(
    identity: str, now: float, window: float, limit: int
) -> bool:
    bucket = _memory_buckets[identity]
    while bucket and (now - bucket[0]) > window:
        bucket.popleft()
    if len(bucket) >= limit:
        return False
    bucket.append(now)
    return True


async def redis_try_consume(
    client: aioredis.Redis,
    identity: str,
    now: float,
    window: float,
    limit: int,
) -> bool:
    key = f"precodahora:rl:{identity}"
    member = f"{now}:{uuid.uuid4().hex}"
    result = await client.eval(
        _SLIDING_WINDOW_LUA,
        1,
        key,
        str(now),
        str(window),
        str(limit),
        member,
    )
    return bool(result)


async def try_consume_rate_slot(identity: str) -> bool:
    now = time.time()
    window = float(settings.rate_limit_window_seconds)
    limit = settings.rate_limit_requests_per_minute

    if not settings.redis_url.strip():
        return memory_try_consume(identity, now, window, limit)

    client = get_async_redis()
    if client is None:
        logger.warning("redis_rate_limit_no_client_fallback identity=%s", identity)
        return memory_try_consume(identity, now, window, limit)

    try:
        return await redis_try_consume(client, identity, now, window, limit)
    except Exception:
        logger.exception("redis_rate_limit_error_fallback identity=%s", identity)
        return memory_try_consume(identity, now, window, limit)

