from typing import TypedDict, List, Any
from pathlib import Path
from docling.datamodel.document import DoclingDocument

class WorkflowState(TypedDict):
    # Inputs
    job_id: str
    file_path: str
    output_dir: str
    
    # Internal artifacts
    doc_object: DoclingDocument         
    raw_images: List[Any]  
    filtered_images: List[Any] 
    
    # Metrics
    saved_count: int