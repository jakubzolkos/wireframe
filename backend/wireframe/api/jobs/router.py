from fastapi import APIRouter, HTTPException, Request
from arq.jobs import Job, JobStatus

router = APIRouter()

@router.get("/{job_id}")
async def get_job_status(job_id: str, request: Request):
    """
    Check the status and result of a background job.
    """
    try:
        job = Job(job_id, request.app.state.arq_pool)
        status = await job.status()
        
        response = {
            "job_id": job_id,
            "status": status.value, # Convert enum to string
        }
        
        if status == JobStatus.complete:
            response["result"] = await job.result()
        elif status == JobStatus.in_progress:
            response["message"] = "Job is currently running"
        elif status == JobStatus.queued:
            response["message"] = "Job is queued"
        elif status == JobStatus.failed:
            # We can try to get the exception info if needed, but result() re-raises the exception
            # by default if we don't handle it. job.result() will raise the exception.
            # To get exception safely without crashing this endpoint:
            try:
                await job.result()
            except Exception as e:
                response["error"] = str(e)
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Job not found or error: {str(e)}")
