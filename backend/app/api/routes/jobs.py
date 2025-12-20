from uuid import UUID
from fastapi import APIRouter, Path
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.database import Job, Design, BOMItem, CircuitComponent
from app.models.schemas import StreamEvent, JobStatusResponse, FinalDesignResponse, DesignMetadata, DesignParameters, CircuitDesign, SchematicNode, Net, BOMItemResponse, DownloadLinks
from app.services.database import get_db_session
from app.core.graph_builder import build_graph
from app.utils.logging import get_logger
import json

router = APIRouter(prefix="/jobs", tags=["jobs"])
logger = get_logger(__name__)


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: UUID = Path(...)):
    await logger.ainfo("job_status_request", job_id=str(job_id))

    async for session in get_db_session():
        result = await session.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        
        if not job:
            return JobStatusResponse(
                job_id=job_id,
                status="not_found",
                created_at=job.created_at if job else None,
                updated_at=job.updated_at if job else None,
            )

        design_data = None
        design_result = await session.execute(select(Design).where(Design.job_id == job_id))
        design = design_result.scalar_one_or_none()
        
        if design:
            bom_result = await session.execute(select(BOMItem).where(BOMItem.design_id == design.id))
            bom_items = bom_result.scalars().all()
            
            comp_result = await session.execute(select(CircuitComponent).where(CircuitComponent.design_id == design.id))
            components = comp_result.scalars().all()

            design_data = FinalDesignResponse(
                job_id=job_id,
                status=job.status,
                metadata=DesignMetadata(
                    device_name=design.device_name,
                    datasheet_title=design.datasheet_title,
                ),
                design_parameters=DesignParameters(),
                circuit_design=CircuitDesign(
                    schematic_nodes=[
                        SchematicNode(
                            ref=comp.ref_des,
                            lib="Device:R" if comp.ref_des.startswith("R") else "Device:C",
                            value=comp.value,
                            pos=[comp.x_pos or 0.0, comp.y_pos or 0.0] if comp.x_pos and comp.y_pos else None,
                        )
                        for comp in components
                    ],
                    nets=[],
                ),
                bom=[
                    BOMItemResponse(
                        reference=item.reference,
                        part_number=item.part_number,
                        manufacturer=item.manufacturer,
                        description=item.description,
                        value=item.value,
                        quantity=item.quantity,
                        package=item.package,
                    )
                    for item in bom_items
                ],
                download_links=DownloadLinks(
                    kicad_sch=f"/jobs/{job_id}/artifacts/schematic.kicad_sch"
                ),
            )

        return JobStatusResponse(
            job_id=job_id,
            status=job.status,
            created_at=job.created_at,
            updated_at=job.updated_at,
            design=design_data,
        )


@router.get("/{job_id}/stream")
async def stream_job_status(job_id: UUID = Path(...)):
    await logger.ainfo("stream_request", job_id=str(job_id))

    async def event_generator():
        graph = build_graph()
        config = {"configurable": {"thread_id": str(job_id)}}

        try:
            async for event in graph.astream_events(None, config=config, version="v2"):
                if event["event"] == "on_chain_end":
                    node_name = event.get("name", "unknown")
                    data = {
                        "node": node_name,
                        "status": "completed",
                        "message": f"{node_name} completed",
                    }
                    yield f"event: agent_update\ndata: {json.dumps(data)}\n\n"

                elif event["event"] == "on_chain_start":
                    node_name = event.get("name", "unknown")
                    data = {
                        "node": node_name,
                        "status": "processing",
                        "message": f"{node_name} started",
                    }
                    yield f"event: agent_update\ndata: {json.dumps(data)}\n\n"

                elif event["event"] == "on_chain_error":
                    data = {
                        "node": "error",
                        "status": "error",
                        "message": str(event.get("error", "Unknown error")),
                    }
                    yield f"event: error\ndata: {json.dumps(data)}\n\n"

        except Exception as e:
            await logger.aerror("stream_error", job_id=str(job_id), error=str(e))
            data = {"error": "Stream error", "message": str(e)}
            yield f"event: error\ndata: {json.dumps(data)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
