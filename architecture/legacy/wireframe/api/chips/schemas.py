from typing import Literal

from autopcb.datatypes.pcb import Footprint
from autopcb.datatypes.schematics import LibSymbol
from pydantic import BaseModel


class ChipSearchItem(BaseModel):
    uid: str
    mpn: str
    manufacturer: str
    symbol: LibSymbol
    footprint: Footprint | None = None
    datasheet: str | None = None
    description: str | None = None
    package: str | None = None
    source: Literal["ultralibrarian", "jlc", "digikey"]

class ChipCategory(BaseModel):
    id: str
    name: str
    description: str | None = None
    parent_id: str | None = None
    children: list["ChipCategory"] | None = None

class ChipFilterMultichoiceValue(BaseModel):
    value: str
    num_chips_with_value: int
class ChipFilterMultichoice(BaseModel):
    type: Literal["multichoice"]
    name: str
    alias: str
    default: str
    available_values: list[ChipFilterMultichoiceValue]

class ChipFilterPhysicalUnitRange(BaseModel):
    type: Literal["physical_unit_range"]
    name: str
    alias: str
    available_units: list[str]
    product_count: int
    unique_value_count: int

class ChipSubcategoryInfo(BaseModel):
    name: str
    component_count: int
    category_id: str