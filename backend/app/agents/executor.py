from typing import Any
from app.core.graph_state import GraphState
from app.services.e2b_client import e2b_service
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def executor_node(state: dict[str, Any]) -> dict[str, Any]:
    await logger.ainfo("executor_start")
    
    graph_state = GraphState(**state)
    
    script = None
    for msg in reversed(graph_state.messages):
        if isinstance(msg, dict) and msg.get("role") == "math_engineer":
            content = msg.get("content", "")
            if "Generated script:" in content:
                script = content.split("Generated script:")[1].strip()
                if script.endswith("..."):
                    script = script[:-3]
            break

    if not script:
        await logger.aerror("no_script_found")
        return {"error_log": ["No script found from math engineer"], "next_node": "end"}

    try:
        result = await e2b_service.execute_script(script)
        await logger.ainfo("executor_complete", calculated_values=list(result.keys()))

        return {
            "calculated_bom": result,
            "next_node": "end",
        }
    except Exception as e:
        await logger.aerror("executor_error", error=str(e))
        return {"error_log": [f"Executor error: {str(e)}"], "next_node": "end"}
