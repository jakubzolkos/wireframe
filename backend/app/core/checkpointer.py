from langgraph.checkpoint.postgres import PostgresSaver
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

_engine = None
_checkpointer = None


def get_checkpointer() -> PostgresSaver:
    global _checkpointer
    if _checkpointer is None:
        db_url = settings.database_url.replace("+asyncpg", "")
        _checkpointer = PostgresSaver.from_conn_string(db_url)
    return _checkpointer
