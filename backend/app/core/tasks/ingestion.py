import structlog
from app.infrastructure.adapters.marker import pdf_ingestion_service

log = structlog.get_logger()

async def process_pdf_job(ctx, file_path: str, job_id: str):
    """
    Arq task to process a PDF file.
    
    Args:
        ctx: Arq context
        file_path: Path to the local PDF file (in shared volume)
        job_id: Unique job identifier
    """
    log.info("task_start", job_id=job_id, file_path=file_path)
    
    try:
        # Run the heavy processing
        # This is CPU/GPU bound.
        # Ideally, we should ensure the file is accessible.
        # The worker and API must share the volume where the file is stored.
        
        result = pdf_ingestion_service.process_file(file_path)
        
        # TODO: Save result to Database/S3 associated with job_id
        # For now, we return it. Arq stores the result in Redis for a short time.
        
        log.info("task_complete", job_id=job_id)
        return result
        
    except Exception as e:
        log.error("task_failed", job_id=job_id, error=str(e))
        raise e

