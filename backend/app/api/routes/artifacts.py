from uuid import UUID
from fastapi import APIRouter, Path
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.database import Job, Design, Artifact
from app.services.database import get_db_session
from app.services.storage import storage_service
from app.services.kicad_generator import generate_kicad_schematic
from app.core.graph_state import GraphState
from app.core.graph_builder import build_graph
from app.utils.logging import get_logger

router = APIRouter(prefix="/jobs", tags=["artifacts"])
logger = get_logger(__name__)


@router.get("/{job_id}/artifacts/schematic.kicad_sch")
async def download_schematic(job_id: UUID = Path(...)):
    await logger.ainfo("schematic_download_request", job_id=str(job_id))

    try:
        graph = build_graph()
        config = {"configurable": {"thread_id": str(job_id)}}

        state_snapshot = await graph.aget_state(config)
        if not state_snapshot:
            return Response(status_code=404, content="Job state not found")

        state = GraphState(**state_snapshot.values)
        schematic_content = generate_kicad_schematic(state)

        file_key = f"jobs/{job_id}/schematic.kicad_sch"
        await storage_service.store_artifact(
            schematic_content.encode("utf-8"),
            file_key,
            "application/x-kicad-schematic",
        )

        return Response(
            content=schematic_content,
            media_type="application/x-kicad-schematic",
            headers={"Content-Disposition": f'attachment; filename="schematic_{job_id}.kicad_sch"'},
        )
    except Exception as e:
        await logger.aerror("schematic_download_error", job_id=str(job_id), error=str(e))
        return Response(status_code=500, content=f"Error generating schematic: {str(e)}")


@router.get("/{job_id}/artifacts/bom.csv")
async def download_bom(job_id: UUID = Path(...)):
    await logger.ainfo("bom_download_request", job_id=str(job_id))

    try:
        async for session in get_db_session():
            result = await session.execute(
                select(Design).where(Design.job_id == job_id)
            )
            design = result.scalar_one_or_none()
            if not design:
                return Response(status_code=404, content="Design not found")

            bom_items = design.bom_items
            csv_lines = ["Reference,Part Number,Manufacturer,Description,Value,Quantity,Package"]
            for item in bom_items:
                csv_lines.append(
                    f"{item.reference},{item.part_number or ''},{item.manufacturer or ''},"
                    f"{item.description or ''},{item.value or ''},{item.quantity},{item.package or ''}"
                )

            csv_content = "\n".join(csv_lines)
            return Response(
                content=csv_content,
                media_type="text/csv",
                headers={"Content-Disposition": f'attachment; filename="bom_{job_id}.csv"'},
            )
    except Exception as e:
        await logger.aerror("bom_download_error", job_id=str(job_id), error=str(e))
        return Response(status_code=500, content=f"Error generating BOM: {str(e)}")
