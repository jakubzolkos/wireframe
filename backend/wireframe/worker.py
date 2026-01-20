import logging
import sys

from arq.connections import RedisSettings
from wireframe.config import settings
from wireframe.agents.workflow import build_extraction_workflow

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
    force=True
)

logger = logging.getLogger(__name__)

# Compile graph once at startup
extraction_app = build_extraction_workflow()

async def ingest_datasheet(ctx, file_id: str, file_path: str, output_dir: str):
    """
    The ARQ task. It invokes the LangGraph application.
    """
    logger.info(f"[{file_id}] Starting Extraction Task")
    
    initial_state = {
        "job_id": file_id,
        "file_path": file_path,
        "output_dir": output_dir,
        "doc_object": None,
        "raw_images": [],
        "filtered_images": [],
        "saved_count": 0
    }
    
    result = await extraction_app.ainvoke(initial_state)
    
    logger.info(f"[{file_id}] Workflow Complete. Saved {result['saved_count']} images.")
    return result['saved_count']

class WorkerSettings:
    functions = [ingest_datasheet]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)