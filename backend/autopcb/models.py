import collections
from typing import Dict, List, Literal, Generic, TypeVar, Union
from dataclasses import dataclass, field

from libcst._position import CodeRange

from autopcb.datatypes.pcb import Board, Footprint
from autopcb.datatypes.schematics import LibSymbol
from autopcb.datatypes.mixins import DataclassSerializerMixin

T = TypeVar('T')


@dataclass(kw_only=True)
class ArgInfoGuiOptions(Generic[T]):
    visible: bool = False
    editable: bool = True
    is_filter: bool = False
    # Dacite parsing library doesn't seem to support list[T] | None
    choices: Union[list[T], None] = None


@dataclass(kw_only=True)
class ArgInfo(Generic[T]):
    value: T
    position: CodeRange
    gui: ArgInfoGuiOptions[T] = field(default_factory=ArgInfoGuiOptions)


@dataclass(kw_only=True)
class ArgInfoVar(ArgInfo[str]):
    """Represents a Python expression (not only variables) such as BUS[i+4]"""
    formatting: Literal['var'] = 'var'  # .formatting is a tag that is used by the frontend to know how this attribute should be presented (ex. <a> for URL, <input type='number> for int, etc.)


@dataclass(kw_only=True)
class ArgInfoStr(ArgInfo[str]):
    formatting: Literal['str'] = 'str'


@dataclass(kw_only=True)
class ArgInfoInt(ArgInfo[int]):
    formatting: Literal['int'] = 'int'


@dataclass(kw_only=True)
class ArgInfoFloat(ArgInfo[float]):
    formatting: Literal['float'] = 'float'


@dataclass(kw_only=True)
class ArgInfoBool(ArgInfo[bool]):
    formatting: Literal['bool'] = 'bool'


@dataclass(kw_only=True)
class ArgInfoNone(ArgInfo[None]):
    formatting: Literal['none'] = 'none'


@dataclass(kw_only=True)
class ArgInfoUrl(ArgInfo[str]):
    formatting: Literal['url'] = 'url'


@dataclass(kw_only=True)
class ArgInfoArray(ArgInfo[T], Generic[T]):
    formatting: Literal['array'] = 'array'
    # we have to manually override ArgInfo.value because the parsing library dacite doesn't correctly
    # forward ArgInfo[list[T]] but rather lets value: T which is wrong
    value: list[T]


@dataclass(kw_only=True)
class ArgInfoChoice(ArgInfo[T], Generic[T]):
    formatting: Literal['choice'] = 'choice'


@dataclass(kw_only=True)
class ArgInfoMultiChoice(ArgInfo[list[T]], Generic[T]):
    formatting: Literal['multichoice'] = 'multichoice'


@dataclass(kw_only=True)
class ArgInfoInterdependent(ArgInfo[str]):
    formatting: Literal['interdependent'] = 'interdependent'


@dataclass(kw_only=True)
class ArgInfoPhysicalUnitRange(ArgInfo[str], Generic[T]):
    formatting: Literal['physical_unit_range'] = 'physical_unit_range'


@dataclass(kw_only=True)
class LCSCPartInfo:
    part_name: str
    ref_prefix: str


@dataclass(kw_only=True)
class FirstAndLastLine:  # of the code of a subcircuit class
    first_line: int
    last_line: int


@dataclass(kw_only=True)
class BOMEntry:
    reference: str
    value: str
    footprint: str
    datasheet: str | None = None
    chip_id: str


@dataclass(kw_only=True)
class Component:
    varname: ArgInfoVar

@dataclass(kw_only=True)
class Parameter(Component):
    constructor: Literal['Parameter'] = 'Parameter'
    current_value: bool | int | float | str
    default: ArgInfoStr | ArgInfoInt | ArgInfoFloat | ArgInfoBool
    choices: ArgInfoArray[str] | None = None
    description: ArgInfoStr


@dataclass(kw_only=True)
class Chip(Component, DataclassSerializerMixin):
    constructor: Literal['Part'] = 'Part'
    chip_id: ArgInfoStr
    unit: ArgInfoChoice[int]
    variant: ArgInfoChoice[int]
    x: ArgInfoInt
    y: ArgInfoInt
    rotate: ArgInfoInt
    reflect: ArgInfoStr
    datasheet: ArgInfoUrl
    mpn: ArgInfoStr
    ref_position: ArgInfoChoice[str]


@dataclass(kw_only=True)
class Port(Component):
    constructor: Literal['Port'] = 'Port'
    chip_id: ArgInfoStr
    pins: ArgInfoArray[str]
    side: ArgInfoChoice[str]
    x: ArgInfoInt
    y: ArgInfoInt


@dataclass(kw_only=True)
class Text(Component):
    constructor: Literal['Text'] = 'Text'
    content: ArgInfoStr
    size: ArgInfoInt
    x: ArgInfoInt
    y: ArgInfoInt


@dataclass(kw_only=True)
class Power(Component):
    constructor: Literal['Power'] = 'Power'
    chip_id: ArgInfoStr
    name: ArgInfoStr
    x: ArgInfoInt
    y: ArgInfoInt
    rotate: ArgInfoInt
    reflect: ArgInfoStr


@dataclass(kw_only=True)
class GND(Component):
    constructor: Literal['GND'] = 'GND'
    chip_id: ArgInfoStr
    x: ArgInfoInt
    y: ArgInfoInt
    rotate: ArgInfoInt
    reflect: ArgInfoStr


@dataclass(kw_only=True)
class NoConnect(Component):
    constructor: Literal['NoConnect'] = 'NoConnect'
    chip_id: ArgInfoStr
    x: ArgInfoInt
    y: ArgInfoInt


@dataclass(kw_only=True)
class NetLabel(Component):
    constructor: Literal['NetLabel'] = 'NetLabel'
    chip_id: ArgInfoStr 
    net: ArgInfoStr 
    x: ArgInfoInt 
    y: ArgInfoInt 
    rotate: ArgInfoInt 
    reflect: ArgInfoStr


@dataclass(kw_only=True)
class PinId(DataclassSerializerMixin):
    name: str
    number: str


@dataclass(kw_only=True)
class Connection:
    parent_component_a_uuid: str
    parent_component_b_uuid: str
    pid_a: PinId
    pid_b: PinId
    pin_a: ArgInfoChoice[str]
    pin_b: ArgInfoChoice[str]
    vertices: ArgInfoArray[tuple[int, int]]
    current: ArgInfoChoice[str]
    uuid: str


@dataclass(kw_only=True)
class FrontendPort:
    name: str
    side: Literal['left', 'right']
    pins: List[str]
    is_parameter: bool = False


@dataclass(kw_only=True)
class FrontendBlockInfo:
    subcircuit_id: str
    name: str
    ports: List[FrontendPort] = field(default_factory=list)
    parameters: List[Parameter] = field(default_factory=list)
    description: str | None = None


@dataclass(kw_only=True)
class SvelteFlowEdgeData:
    current: float = 0


@dataclass(kw_only=True)
class SvelteFlowEdge:
    id: str
    data: SvelteFlowEdgeData
    # selected: bool  # this is explicitly excluded on the frontend before saving on firebase
    source: str
    sourceHandle: str
    target: str
    targetHandle: str


@dataclass(kw_only=True)
class SvelteFlowPosition:
    x: float
    y: float


@dataclass(kw_only=True)
class SvelteFlowData:
    params: Dict[str, bool | int | float | str] = field(default_factory=dict)
    subcircuit_info: FrontendBlockInfo
    show_parameter_box: bool = True


@dataclass(kw_only=True)
class SvelteFlowNode:
    data: SvelteFlowData
    # dragging: bool  # this is explicitly excluded on the frontend before saving on firebase
    id: str
    origin: List[float]
    position: SvelteFlowPosition
    # selected: bool  # this is explicitly excluded on the frontend before saving on firebase
    type: Literal["CustomNode"]


@dataclass(kw_only=True)
class SvelteFlowJson(DataclassSerializerMixin):
    nodes: List[SvelteFlowNode]
    edges: List[SvelteFlowEdge]


@dataclass(kw_only=True)
class SubcircuitChip(DataclassSerializerMixin):
    symbol: LibSymbol
    footprint: Footprint | None = None


@dataclass(kw_only=True)
class BlockDiagramFileContent(DataclassSerializerMixin):
    block_diagram_svelteflow_json: SvelteFlowJson
    kicad_pcb: Board | None


@dataclass(kw_only=True)
class BlockDiagram(DataclassSerializerMixin):
    file_name: str
    file_id: str
    version_timestamp: str
    description: str | None
    category: str | None
    file_content: BlockDiagramFileContent


@dataclass(kw_only=True)
class PCB(DataclassSerializerMixin):
    kicad_pcb: Board
    bill_of_materials: Dict[str, List[BOMEntry]]
    header_file: str
    node_metadata: dict[str, FrontendBlockInfo]


@dataclass(kw_only=True)
class GenerationFeedback:
    message: str
    component_type: Literal['node'] | Literal['edge'] = 'node'
    component_id: str


@dataclass(kw_only=True)
class PCBGenerationResult(DataclassSerializerMixin):
    pcb: PCB | None = None
    feedback: GenerationFeedback | None = None


@dataclass(kw_only=True)
class ParsedSubcircuit(DataclassSerializerMixin):
    components: Dict[str, Chip | Port | Text | Power | NoConnect | NetLabel | GND] = field(default_factory=dict)
    connections: Dict[str, Connection]
    parameters: Dict[str, Parameter]
    chips: Dict[str, SubcircuitChip]
    build_func_line_bounds: FirstAndLastLine

@dataclass(kw_only=True)
class RawSubcircuit(DataclassSerializerMixin):
    file_name: str
    file_id: str
    python_source_code: str
    chips: Dict[str, SubcircuitChip]
    user_parameter_values: Dict[str, str | int | float | bool]


@dataclass
class PyodideError:
    name: str
    message: str
    type: str
    __error_address: int


@dataclass(kw_only=True)
class SubcircuitContent(DataclassSerializerMixin):
    parsed: ParsedSubcircuit
    python_source_code: str
    pyodideError: PyodideError | None = None


@dataclass
class ParsedChip(DataclassSerializerMixin):
    symbol: LibSymbol
    # Optional for symbols like GND which don't have a footprint
    footprint: Footprint | None = None


@dataclass
class ParsedSchematic(DataclassSerializerMixin):
    source_code: str
    chips: Dict[str, ParsedChip]