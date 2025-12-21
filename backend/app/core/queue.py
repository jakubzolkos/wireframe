from arq.connections import RedisSettings
from app.core.config import settings

def get_redis_settings() -> RedisSettings:
    """
    Parse the REDIS_URL to return arq RedisSettings.
    """
    # Simple parsing assuming standard format redis://host:port/db
    # For a robust production app, use urllib.parse or similar
    url = settings.REDIS_URL
    if "://" not in url:
        host, port = "localhost", 6379
        db = 0
    else:
        # e.g. redis://redis:6379/0
        params = url.split("://")[1]
        host_port, db = params.split("/")
        if ":" in host_port:
            host, port = host_port.split(":")
            port = int(port)
        else:
            host, port = host_port, 6379
        db = int(db) if db else 0

    return RedisSettings(host=host, port=port, database=db)
