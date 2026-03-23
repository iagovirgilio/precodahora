import asyncio
from unittest.mock import AsyncMock, MagicMock

from app.rate_limiting import redis_try_consume


def test_redis_try_consume_permite_quando_script_retorna_um():
    async def _run() -> None:
        client = MagicMock()
        client.eval = AsyncMock(return_value=1)
        ok = await redis_try_consume(client, "id-test", 1_000.0, 60.0, 5)
        assert ok is True
        client.eval.assert_called_once()

    asyncio.run(_run())


def test_redis_try_consume_nega_quando_script_retorna_zero():
    async def _run() -> None:
        client = MagicMock()
        client.eval = AsyncMock(return_value=0)
        ok = await redis_try_consume(client, "id-test", 1_000.0, 60.0, 5)
        assert ok is False

    asyncio.run(_run())
