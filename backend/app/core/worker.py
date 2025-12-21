import structlog
from arq import run_worker
from app.core.queue import get_redis_settings
from app.tasks.ingestion import process_pdf_job
from app.infrastructure.adapters.marker import pdf_ingestion_service

log = structlog.get_logger()

async def startup(ctx):
    log.info("worker_startup")
    try:
        pdf_ingestion_service.initialize_model()
    except Exception as e:
        log.error("worker_startup_failed", error=str(e))
        raise

async def shutdown(ctx):
    log.info("worker_shutdown")

class WorkerSettings:
    functions = [process_pdf_job]
    redis_settings = get_redis_settings()
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 1

if __name__ == "__main__":
    run_worker(WorkerSettings)

