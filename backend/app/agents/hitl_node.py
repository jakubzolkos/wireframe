from typing import Any
from app.core.graph_state import GraphState
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def hitl_node(state: dict[str, Any]) -> dict[str, Any]:
    await logger.ainfo("hitl_node_triggered")
    
    graph_state = GraphState(**state)
    
    missing = graph_state.missing_variables
    
    await logger.ainfo("hitl_interrupt", missing_variables=missing)
    
    return {
        "next_node": "end",
        "messages": [{"role": "hitl", "content": f"Missing variables: {', '.join(missing)}"}],
    }
