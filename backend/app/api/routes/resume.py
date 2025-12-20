from uuid import UUID
from fastapi import APIRouter, Path, Body, status
from app.models.schemas import ResumeRequest, ResumeResponse
from app.core.graph_builder import build_graph
from app.core.graph_state import GraphState
from app.utils.logging import get_logger

router = APIRouter(prefix="/jobs", tags=["jobs"])
logger = get_logger(__name__)


@router.post("/{job_id}/resume", response_model=ResumeResponse)
async def resume_job(
    job_id: UUID = Path(...),
    request: ResumeRequest = Body(...),
):
    await logger.ainfo("resume_request", job_id=str(job_id), variables=list(request.missing_variables.keys()))

    try:
        graph = build_graph()
        config = {"configurable": {"thread_id": str(job_id)}}

        state_snapshot = await graph.aget_state(config)
        if not state_snapshot:
            return ResumeResponse(
                job_id=job_id,
                status="error",
                message="Job state not found",
            )

        current_state = GraphState(**state_snapshot.values)
        current_state.user_inputs.update(request.missing_variables)
        current_state.missing_variables = []

        await graph.ainvoke(current_state.model_dump(), config=config)

        return ResumeResponse(
            job_id=job_id,
            status="resumed",
            message="Job resumed successfully",
        )
    except Exception as e:
        await logger.aerror("resume_error", job_id=str(job_id), error=str(e))
        return ResumeResponse(
            job_id=job_id,
            status="error",
            message=f"Resume failed: {str(e)}",
        )
