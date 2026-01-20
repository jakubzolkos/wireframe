from langgraph.graph import StateGraph, END
from .state import WorkflowState
from .nodes import parse_node, classify_node, save_node

def build_extraction_workflow():
    workflow = StateGraph(WorkflowState)
    
    # Nodes
    workflow.add_node("ingest", parse_node)
    workflow.add_node("classify", classify_node) # Renamed from 'filter'
    workflow.add_node("save", save_node)
    
    # Edges
    workflow.set_entry_point("ingest")
    workflow.add_edge("ingest", "classify")
    workflow.add_edge("classify", "save")
    workflow.add_edge("save", END)
    
    return workflow.compile()