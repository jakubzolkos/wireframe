from typing import List, Optional, TypedDict
from pydantic import BaseModel, Field, ConfigDict
from docling.datamodel.document import DoclingDocument


ComponentDict = TypedDict('ComponentDict', {
    'bbox': List[float],
    'class': str,
    'confidence': float,
    'id': str
}, total=False)


class NetDict(TypedDict, total=False):
    net_id: str
    connected_components: List[str]


ExtractedCircuitBase = TypedDict('ExtractedCircuitBase', {
    'components': List[ComponentDict],
    'netlist': List[NetDict]
}, total=False)

class ExtractedCircuitDict(TypedDict, total=False):
    components: List[ComponentDict]
    netlist: List[NetDict]
    source_image_id: str
    section_title: str
    caption: Optional[str]


class ImageDataDict(TypedDict, total=False):
    id: str
    image: bytes
    section_title: str
    caption: Optional[str]


class PinDict(TypedDict, total=False):
    name: str
    location: List[float]

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
    
    extracted_circuits: List[ExtractedCircuitDict] = Field(default_factory=list)

    # Metrics
    saved_count: int = 0
    
    model_config = ConfigDict(arbitrary_types_allowed=True)

class SaveResult(BaseModel):
    saved_count: int


class ExtractedComponent(BaseModel):
    id: str
    label: str  # e.g., "R1", "C2", "U1"
    category: str # e.g., "Resistor", "Capacitor", "IC_Main"
    bbox: tuple[float, float, float, float] # x1, y1, x2, y2
    pins: List[PinDict]

class ExtractedNet(BaseModel):
    id: str
    nodes: List[str] # List of Component Pin IDs connected to this net
