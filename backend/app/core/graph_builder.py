from typing import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from app.core.graph_state import GraphState
from app.core.checkpointer import get_checkpointer
from app.agents.ingestion_supervisor import ingestion_supervisor_node
from app.agents.vision_agent import vision_agent_node
from app.agents.constants_miner import constants_miner_node
from app.agents.equation_extractor import equation_extractor_node
from app.agents.math_engineer import math_engineer_node
from app.agents.executor import executor_node
from app.agents.hitl_node import hitl_node
from app.utils.logging import get_logger

logger = get_logger(__name__)


class GraphStateDict(TypedDict):
    pdf_chunks: list
    schematic_image_path: str | None
    extracted_constants: dict
    design_equations: list
    user_inputs: dict
    missing_variables: list
    netlist_topology: dict
    abstract_netlist: list
    calculated_bom: dict
    messages: list
    next_node: str | None
    error_log: list


def build_graph() -> StateGraph:
    checkpointer = get_checkpointer()

    workflow = StateGraph(GraphStateDict)

    workflow.add_node("ingestion_supervisor", ingestion_supervisor_node)
    workflow.add_node("vision_agent", vision_agent_node)
    workflow.add_node("constants_miner", constants_miner_node)
    workflow.add_node("equation_extractor", equation_extractor_node)
    workflow.add_node("math_engineer", math_engineer_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("hitl", hitl_node)

    workflow.set_entry_point("ingestion_supervisor")

    workflow.add_conditional_edges(
        "ingestion_supervisor",
        _route_from_ingestion,
        {
            "vision_agent": "vision_agent",
            "constants_miner": "constants_miner",
            "equation_extractor": "equation_extractor",
            "end": END,
        },
    )

    workflow.add_edge("vision_agent", "constants_miner")
    workflow.add_edge("constants_miner", "equation_extractor")
    workflow.add_edge("equation_extractor", "math_engineer")

    workflow.add_conditional_edges(
        "math_engineer",
        _route_from_math_engineer,
        {
            "executor": "executor",
            "hitl": "hitl",
            "end": END,
        },
    )

    workflow.add_edge("executor", END)
    workflow.add_edge("hitl", END)

    app = workflow.compile(checkpointer=checkpointer)
    return app


def _route_from_ingestion(state: GraphStateDict) -> str:
    if state.get("schematic_image_path"):
        return "vision_agent"
    if any("table" in chunk.get("chunk_type", "").lower() for chunk in state.get("pdf_chunks", [])):
        return "constants_miner"
    if state.get("pdf_chunks"):
        return "equation_extractor"
    return "end"


def _route_from_math_engineer(state: GraphStateDict) -> str:
    if state.get("missing_variables"):
        return "hitl"
    if state.get("design_equations"):
        return "executor"
    return "end"
