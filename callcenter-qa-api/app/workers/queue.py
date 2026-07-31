from functools import lru_cache

from arq import ArqRedis, create_pool
from arq.connections import RedisSettings

from app.config import settings


@lru_cache
def _redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(settings.redis_url)


_pool: ArqRedis | None = None


async def get_arq_pool() -> ArqRedis:
    """Lazily-created, process-wide arq connection pool used by API routes to
    enqueue background jobs (transcription, QA evaluation)."""
    global _pool
    if _pool is None:
        _pool = await create_pool(_redis_settings())
    return _pool
