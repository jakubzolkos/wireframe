from uuid import uuid4
from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, status, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.database import Job
from app.models.schemas import AnalyzeRequest, AnalyzeResponse
from app.services.database import get_db_session
from app.services.storage import storage_service
from app.services.pdf_parser import pdf_parser_service
from app.core.graph_builder import build_graph
from app.core.graph_state import GraphState
from app.utils.logging import get_logger
import json

router = APIRouter(prefix="/analyze", tags=["analyze"])
logger = get_logger(__name__)


@router.post("", response_model=AnalyzeResponse, status_code=status.HTTP_202_ACCEPTED)
async def analyze_datasheet(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_constraints: str = Form("{}"),
):
    job_id = uuid4()
    
    await logger.ainfo("analyze_request", job_id=str(job_id), filename=file.filename)

    try:
        constraints = json.loads(user_constraints) if user_constraints else {}
        pdf_content = await file.read()

        file_key = f"jobs/{job_id}/{file.filename}"
        await storage_service.upload_pdf(pdf_content, file_key)

        async for session in get_db_session():
            job = Job(
                id=job_id,
                status="PENDING",
                pdf_path=file_key,
            )
            session.add(job)
            await session.commit()
            break

        background_tasks.add_task(process_datasheet_job, str(job_id), file_key, constraints)

        return AnalyzeResponse(
            job_id=job_id,
            status="PENDING",
            created_at=job.created_at,
        )
    except Exception as e:
        await logger.aerror("analyze_error", job_id=str(job_id), error=str(e))
        raise


async def process_datasheet_job(job_id: str, pdf_path: str, user_constraints: dict):
    await logger.ainfo("job_processing_start", job_id=job_id)
    
    try:
        async for session in get_db_session():
            result = await session.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                await logger.aerror("job_not_found", job_id=job_id)
                return

            job.status = "PROCESSING"
            await session.commit()

        pdf_content = await storage_service.download_file(pdf_path)
        chunks, schematic_path = await pdf_parser_service.parse_pdf(pdf_content, pdf_path)

        initial_state = GraphState(
            pdf_chunks=chunks,
            schematic_image_path=schematic_path,
            user_inputs=user_constraints,
        )

        graph = build_graph()
        config = {"configurable": {"thread_id": job_id}}

        final_state = None
        async for event in graph.astream(initial_state.model_dump(), config=config):
            await logger.ainfo("graph_event", job_id=job_id, event_keys=list(event.keys()))
            final_state = event

        if final_state:
            state_snapshot = await graph.aget_state(config)
            if state_snapshot:
                final_graph_state = GraphState(**state_snapshot.values)
                
                async for session in get_db_session():
                    job.status = "COMPLETED"
                    
                    from app.models.database import Design, BOMItem, CircuitComponent
                    design = Design(
                        job_id=job_id,
                        device_name="Extracted Device",
                        metadata=final_graph_state.model_dump(),
                    )
                    session.add(design)
                    await session.flush()

                    for ref_des, value in final_graph_state.calculated_bom.items():
                        bom_item = BOMItem(
                            design_id=design.id,
                            reference=ref_des,
                            value=str(value),
                            quantity=1,
                        )
                        session.add(bom_item)

                    for comp in final_graph_state.abstract_netlist:
                        circuit_comp = CircuitComponent(
                            design_id=design.id,
                            ref_des=comp.ref_des,
                            value=comp.value,
                            pins=comp.pins,
                            footprint=comp.footprint,
                        )
                        session.add(circuit_comp)

                    await session.commit()
                    break

        await logger.ainfo("job_processing_complete", job_id=job_id)
    except Exception as e:
        await logger.aerror("job_processing_error", job_id=job_id, error=str(e))
        async for session in get_db_session():
            result = await session.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            if job:
                job.status = "FAILED"
                await session.commit()
