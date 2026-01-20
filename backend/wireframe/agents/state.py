from typing import List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from docling.datamodel.document import DoclingDocument

class ImageCandidate(BaseModel):
    id: str
    image: bytes
    section_title: str = "Unknown"
    caption: Optional[str] = None
    
    # Allow arbitrary types for internal image handling if needed
    model_config = ConfigDict(arbitrary_types_allowed=True)

class WorkflowState(BaseModel):
    # Inputs
    job_id: str
    file_path: str
    output_dir: str
    
    # Internal artifacts
    doc_object: Optional[DoclingDocument] = None
    relevant_sections: List[str] = Field(default_factory=list)
    raw_images: List[ImageCandidate] = Field(default_factory=list)
    filtered_images: List[ImageCandidate] = Field(default_factory=list)
    
    # Metrics
    saved_count: int = 0
    
    model_config = ConfigDict(arbitrary_types_allowed=True)

class SaveResult(BaseModel):
    saved_count: int
