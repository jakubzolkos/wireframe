from langgraph.graph import StateGraph, END
from .state import WorkflowState
from .nodes import parse_node, plan_node, extract_node, classify_node, save_node

def build_extraction_workflow():
    # Initialize StateGraph with the Pydantic model
    workflow = StateGraph(WorkflowState)
    
    # Add Nodes
    workflow.add_node("ingest", parse_node)
    workflow.add_node("plan", plan_node)       # New node for section analysis
    workflow.add_node("extract", extract_node) # New node for context-aware extraction
    workflow.add_node("classify", classify_node)
    workflow.add_node("save", save_node)
    
    # Define Edges
    workflow.set_entry_point("ingest")
    
    workflow.add_edge("ingest", "plan")
    workflow.add_edge("plan", "extract")
    workflow.add_edge("extract", "classify")
    workflow.add_edge("classify", "save")
    workflow.add_edge("save", END)
    
    return workflow.compile()
