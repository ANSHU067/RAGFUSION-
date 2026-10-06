"""Infrastructure health checks."""

import asyncio

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.db.session import check_database_connection


async def check_redis_connection(redis: Redis | None) -> bool:
    """Probe the shared async client without owning or closing its pool."""

    if redis is None:
        return False
    try:
        return bool(await asyncio.wait_for(redis.ping(), timeout=2.0))
    except (RedisError, OSError, TimeoutError):
        return False


async def get_health_status(redis_client: Redis | None) -> dict[str, bool | str]:
    """Collect the API dependency statuses."""

    database = await check_database_connection()
    redis = await check_redis_connection(redis_client)
    return {
        "status": "ok" if database and redis else "degraded",
        "database": database,
        "redis": redis,
    }
