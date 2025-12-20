from typing import Any
from app.core.graph_state import GraphState
from app.services.semantic_router import route_chunks
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def ingestion_supervisor_node(state: dict[str, Any]) -> dict[str, Any]:
    await logger.ainfo("ingestion_supervisor_start")
    
    graph_state = GraphState(**state)
    
    if not graph_state.pdf_chunks:
        await logger.awarn("no_chunks_available")
        return {"next_node": None, "error_log": ["No PDF chunks available"]}

    categorized = await route_chunks(graph_state.pdf_chunks)
    
    await logger.ainfo(
        "ingestion_supervisor_routing",
        tables_count=len(categorized.get("tables", [])),
        prose_count=len(categorized.get("prose", [])),
        figures_count=len(categorized.get("figures", [])),
    )

    updated_chunks = (
        categorized.get("tables", [])
        + categorized.get("prose", [])
        + categorized.get("figures", [])
    )

    return {
        "pdf_chunks": [chunk.model_dump() for chunk in updated_chunks],
        "next_node": "vision_agent" if graph_state.schematic_image_path else "constants_miner",
    }
