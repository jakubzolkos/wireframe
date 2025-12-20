from datetime import datetime
from uuid import UUID
from typing import Any
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    user_constraints: dict[str, float] = Field(default_factory=dict)


class AnalyzeResponse(BaseModel):
    job_id: UUID
    status: str
    created_at: datetime


class StreamEvent(BaseModel):
    event: str
    data: dict[str, Any]


class ResumeRequest(BaseModel):
    missing_variables: dict[str, float]


class ResumeResponse(BaseModel):
    job_id: UUID
    status: str
    message: str


class SchematicNode(BaseModel):
    ref: str
    lib: str
    value: str
    pos: list[float] | None = None


class Net(BaseModel):
    name: str
    connections: list[str]


class CircuitDesign(BaseModel):
    schematic_nodes: list[SchematicNode]
    nets: list[Net]


class BOMItemResponse(BaseModel):
    reference: str
    part_number: str | None = None
    manufacturer: str | None = None
    description: str | None = None
    value: str | None = None
    quantity: int = 1
    package: str | None = None


class DesignMetadata(BaseModel):
    device_name: str | None = None
    datasheet_title: str | None = None


class DesignParameters(BaseModel):
    V_in: float | None = None
    V_out: float | None = None
    I_out_max: float | None = None


class DownloadLinks(BaseModel):
    kicad_sch: str


class FinalDesignResponse(BaseModel):
    job_id: UUID
    status: str
    metadata: DesignMetadata
    design_parameters: DesignParameters
    circuit_design: CircuitDesign
    bom: list[BOMItemResponse]
    download_links: DownloadLinks


class JobStatusResponse(BaseModel):
    job_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime
    design: FinalDesignResponse | None = None
