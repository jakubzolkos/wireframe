import uuid
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from arq.connections import ArqRedis
from wireframe.utils.redis import get_redis_pool

router = APIRouter()

# Ensure upload directory exists
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@router.post("/")
async def ingest_datasheet(request: Request, file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    file_id = str(uuid.uuid4())
    # Sanitize filename or just use ID to avoid issues
    safe_filename = f"{file_id}_{file.filename}"
    file_path = UPLOAD_DIR / safe_filename
    
    try:
        # Saving file. Note: This blocks the event loop for the duration of the write.
        # In production, use aiofiles or offload to thread/worker.
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Schedule task
        job = await request.app.state.arq_pool.enqueue_job(
            "ingest_datasheet", 
            file_id,
            str(file_path.absolute()),
            str(UPLOAD_DIR.absolute())
        )
        
        return {
            "message": "Datasheet ingestion started", 
            "job_id": job.job_id,
            "file_id": file_id
        }
        
    except Exception as e:
        # Clean up if possible
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"Failed to process upload: {str(e)}")


