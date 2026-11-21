import redis.asyncio as aioredis

from app.config import settings

# Create a connection pool for async redis
redis_pool = aioredis.ConnectionPool.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    max_connections=50,
)


def get_redis_client() -> aioredis.Redis:
    """Get an async Redis client."""
    return aioredis.Redis(connection_pool=redis_pool)
