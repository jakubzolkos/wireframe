from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from wireframe.config import settings

async def get_redis_pool() -> ArqRedis:
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    return await create_pool(redis_settings)
