from typing import Annotated, Any
from pydantic import BaseModel, Field


def merge_messages(left: list[Any], right: list[Any]) -> list[Any]:
    return left + right


class PDFChunk(BaseModel):
    content: str
    page_number: int
    section_title: str | None = None
    chunk_type: str | None = None


class ExtractedConstant(BaseModel):
    name: str = Field(..., description="Standardized name, e.g., 'V_ref'")
    value: float
    unit: str
    source_context: str = Field(..., description="Snippet verifying the extraction")


class ExtractedEquation(BaseModel):
    target_variable: str
    latex_raw: str
    python_code: str
    dependencies: list[str] = Field(default_factory=list)


class Component(BaseModel):
    ref_des: str
    value: str
    pins: dict[str, str] = Field(default_factory=dict)
    footprint: str | None = None


class GraphState(BaseModel):
    pdf_chunks: list[PDFChunk] = Field(default_factory=list)
    schematic_image_path: str | None = None

    extracted_constants: dict[str, ExtractedConstant] = Field(
        default_factory=dict,
        description="Map of standard names to extracted values",
    )
    design_equations: list[ExtractedEquation] = Field(
        default_factory=list,
        description="All formulas extracted from Application Information",
    )

    user_inputs: dict[str, float] = Field(
        default_factory=dict,
        description="User-defined constraints, e.g., {'V_out': 5.0}",
    )
    missing_variables: list[str] = Field(
        default_factory=list,
        description="Variables preventing equation solution",
    )

    netlist_topology: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Adjacency list representation of the circuit",
    )
    abstract_netlist: list[Component] = Field(default_factory=list)
    calculated_bom: dict[str, float] = Field(
        default_factory=dict,
        description="Final computed values for passives",
    )

    messages: Annotated[list[Any], add] = Field(default_factory=list)
    next_node: str | None = None
    error_log: list[str] = Field(default_factory=list)
