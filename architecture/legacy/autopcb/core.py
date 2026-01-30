from __future__ import annotations

from collections import defaultdict
import copy
from dataclasses import dataclass, field
from functools import lru_cache, wraps
import importlib
import inspect
import itertools
import json
import re
from pathlib import Path
import traceback
from typing import Dict, List, Literal, Set, Tuple
from uuid import uuid4
from urllib.parse import quote

# Imported here just as a check that it's installed, since the frontend imports circuit_tools.py to check if all dependencies can be imported. All other dependencies are imported in this file, so just adding it here for simplicity
import bs4

# These imports are used for parsing the source code of subcircuits
import libcst as cst
from libcst import Call, ClassDef, FunctionDef, ParserSyntaxError
from libcst._position import CodePosition, CodeRange
from libcst.metadata import ParentNodeProvider, PositionProvider
from pydantic import ConfigDict
from pydantic import ConfigDict

from .datatypes.schematics import LibSymbol
from .datatypes.pcb import Footprint
from .exceptions import SubcircuitCodeError, UserFeedback
from .datatypes.templates import PowerSymbol, GNDSymbol, NoConnectSymbol, NetLabelSymbol
from .models import (
    GND,
    ArgInfoArray,
    ArgInfoChoice,
    ArgInfoPhysicalUnitRange,
    ArgInfoGuiOptions,
    ArgInfoInt,
    ArgInfoMultiChoice,
    ArgInfoStr,
    ArgInfoUrl,
    ArgInfoVar,
    BOMEntry,
    Chip,
    NetLabel,
    Port,
    RawSubcircuit,
    ParsedChip,
    SvelteFlowEdge,
    Text,
    Power,
    NoConnect,
    Connection,
    PinId,
    FirstAndLastLine,
    FrontendBlockInfo,
    FrontendPort,
    ParsedSubcircuit,
    Parameter,
    ArgInfoBool, ArgInfoFloat, BlockDiagram
)
from .utils import (
    convert_cst_to_str,
    generate_footprint_uuid,
    get_variable_name_current_function_return_is_assigned_to,
    http_request,
)

# import these so they're available in subcircuits that import: from autopcb.core import *
from .utils import closest_value, e_series, e_series_from_tolerance

DEFAULT_CODE_RANGE = CodeRange(
    start=CodePosition(line=-1, column=-1),
    end=CodePosition(line=-1, column=-1),
)


def exception_info_wrapper(func):
    """Decorator for catching subcircuit code editor errors and the line numbers where they occur."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if isinstance(e, ParserSyntaxError):
                # Libcst errors
                line = int(re.search(r"Syntax Error @ (\d+):", str(e)).group(1))
            else:
                # Standard Python errors
                try:
                    tb_str = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
                    matches = re.findall(r'File "/home/pyodide/subcircuits/[^"]+", line (\d+)', tb_str)
                    line = int(matches[-1])
                except IndexError:
                    # Sanity check to prevent autopcb.core breaking here for yet undiscovered errors
                    # (will not correctly display error line but should not break subcircuits interaction)
                    line = 0

            raise SubcircuitCodeError(line)

    return wrapper

    
@exception_info_wrapper
def parse_subcircuit(raw_subcircuit: RawSubcircuit, enable_logging=True, use_libcst_metadata_wrapper=True) -> ParsedSubcircuit:
    """
    Subcircuits nuit_dataeed to be built with their ports connected to other subcircuits
    to actually make those connections, so this will add mock connections
    to the ports of subcircuit_name for the purposes of rendering an
    individual subcircuit not connected to other subcircuits, and adding
    symbols for the ports as well to be rendered in the subcircuit editor

    Set use_libcst_metadata_wrapper to True if you want to use libcst to parse line and column positions of args
    """
    module = cst.parse_module(Path(f"subcircuits/{raw_subcircuit.file_id}.py").read_text())
    circuit = Circuit(enable_logging=enable_logging)
    subcircuit_module = importlib.import_module("subcircuits." + raw_subcircuit.file_id)
    importlib.reload(subcircuit_module)  # todo fixme find a better way than reloading on first try as well

    # Check if metadata name agrees with class name in the python file
    class_name = None
    for line in module.body:
        if isinstance(line, ClassDef):
            class_def = line
            class_name = class_def.name.value
            break
    if class_name is None:
        raise UserFeedback(f"There seems to be no class defined in the top level of the file {raw_subcircuit.file_name}")

    subcircuit_subclass: type[Subcircuit] = subcircuit_module.__getattribute__(raw_subcircuit.file_name)
    subcircuit_name = subcircuit_subclass.__name__

    if raw_subcircuit.file_name != subcircuit_name:
        raise UserFeedback(f"The file name {raw_subcircuit.file_name} does not match the class name {subcircuit_name}")

    local_chips = raw_subcircuit.chips if raw_subcircuit.chips is not None else {}
    
    # Instantiate the class
    if use_libcst_metadata_wrapper:
        block = subcircuit_subclass(
            instance_id=raw_subcircuit.file_id,
            label=subcircuit_name,
            name=subcircuit_name,
            circuit=circuit,
            store_parsed_info=True,
            local_chips=local_chips,
            user_parameter_values=raw_subcircuit.user_parameter_values,
        )
        visitor = PrintArgumentPosition(block)
        cst.MetadataWrapper(module).visit(visitor)
    else:
        block = subcircuit_subclass(
            instauit_datance_id=raw_subcircuit.file_id,
            label=subcircuit_name,
            name=subcircuit_name,
            circuit=circuit,
            local_chips=local_chips,
            user_parameter_values=raw_subcircuit.user_parameter_values,
        )

    block.build()

    class PrintBuildFunctionPosition(cst.CSTVisitor):
        METADATA_DEPENDENCIES = (PositionProvider,)

        def visit_FunctionDef(self, node: FunctionDef) -> None:
            """This will run on all functions and match those named build to find the start and end of the function's source code"""
            if node.name.value == "build" or node.name.value == "build_component":
                self.class_info_parsed_by_libcst = self.get_metadata(PositionProvider, node)

    module = cst.parse_module(Path(f"subcircuits/{raw_subcircuit.file_id}.py").read_text())
    libcst_metadata_wrapper = cst.MetadataWrapper(module)
    visitor = PrintBuildFunctionPosition()
    libcst_metadata_wrapper.visit(visitor)

    return ParsedSubcircuit(
        components=block.components,
        connections=block.connections,
        chips=block.local_chips,
        parameters=block.parameters,
        build_func_line_bounds=FirstAndLastLine(
            first_line=visitor.class_info_parsed_by_libcst.start.line,
            last_line=visitor.class_info_parsed_by_libcst.end.line,
        ),
    )


@lru_cache(maxsize=128)
def is_parametric_chip(chip_id: str) -> bool:
    if re.match(r'^JLC/C\d+$', chip_id):  # if it's a specific JLC supplier part number like JLC/C1234
        return False
    if not (chip_id.startswith("JLC/") or chip_id.startswith("DigiKey/")):  # parametric chips must start with JLC/ or DigiKey/
        return False

    supplier, subcategory_name = chip_id.split("/")
    categories_response = http_request("get", f"/chips/categories?supplier={supplier.lower()}")
    if categories_response.status_code == 503:
        raise UserFeedback("Chip API of provided supplier is currently unavailable. Cannot resolve parametric chip. Please try again later.")
            
    categories = json.loads(categories_response.content)
    subcategories_aggr = list(itertools.chain.from_iterable(map(lambda x: x['subcategories'], categories)))
    subcategory = next((s for s in subcategories_aggr if s["name"] == subcategory_name), None)
    return subcategory


def get_block_diagram_node_info(subcircuit_instance: Subcircuit) -> FrontendBlockInfo:
    """
    Parses the specified subcircuit from the subcircuits/ directory and retrieves its block diagram parameters
    as a FrontendBlockInfo object.
    """
    new_frontend_block = FrontendBlockInfo(
        name=subcircuit_instance.label,
        subcircuit_id=subcircuit_instance.library_id,
        parameters=list(subcircuit_instance.parameters.values())
    )

    for port in subcircuit_instance.ports.values():
        new_frontend_block.ports.append(
            FrontendPort(
                name=port.name,
                side=port.side,
                pins=list(port.pins.keys()),
                is_parameter=port.is_parameter,
            )
        )

    return new_frontend_block


class PrintArgumentPosition(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider, ParentNodeProvider)

    def __init__(self, subcircuit_instance: Subcircuit):
        super().__init__()
        self.subcircuit_instance = subcircuit_instance

    def visit_Call(self, node: Call):
        """
        If the function call Part or Port, parse its arguments and it's text locations
        """
        if isinstance(node.func, cst.Attribute) and node.func.attr.value in ['Part', 'Port', 'Text', 'Power', 'NoConnect', 'NetLabel', 'Parameter', 'GND']:
            position_of_function = self.get_metadata(PositionProvider, node)
            data_store = {}
            parent = self.get_metadata(ParentNodeProvider, node)

            data_store['varname'] = self.get_metadata(PositionProvider, parent.targets[0].target)
            
            # since the rotation and position args are optional, set the default location if it's not in the arg list to be at the end of the function's arg list, so if the user adds it in the subcircuit editor, it's added there
            arg_list_end_location = position_of_function.end
            data_store['rotate'] = CodeRange(start=arg_list_end_location, end=arg_list_end_location)
            data_store['reflect'] = CodeRange(start=arg_list_end_location, end=arg_list_end_location)
            data_store['unit'] = CodeRange(start=arg_list_end_location, end=arg_list_end_location)
            data_store['variant'] = CodeRange(start=arg_list_end_location, end=arg_list_end_location)
            data_store['ref_position'] = CodeRange(start=arg_list_end_location, end=arg_list_end_location)

            # Handle the first positional argument (chip_id, content, net, name) based on function type
            first_arg_mapping = {
                "Text": "content",  # the first arg of Text(content) is the content
                "NetLabel": "net",   # the first arg of NetLabel(label) is the net label
                "Part": "chip_id",  # the first arg of Part(chip_id) is the chip_id
                "Power": "name"  # the first arg of Power(name) is the power net name
            }
            if node.func.attr.value in first_arg_mapping and len(node.args) > 0:
                data_store[first_arg_mapping[node.func.attr.value]] = self.get_metadata(PositionProvider, node.args[0].value)
            
            for arg in node.args:
                if arg.keyword is None:
                    continue  # skip over non-keyword args, like the first arg of self.Part()
                
                data_store[arg.keyword.value] = self.get_metadata(PositionProvider, arg.value)
            
            self.subcircuit_instance.arg_position_info[position_of_function.start.line] = data_store

        """
        If the function call connect, parse its arguments and their text locations
        """
        if isinstance(node.func, cst.Attribute) and node.func.attr.value == "connect":
            position_of_function = self.get_metadata(PositionProvider, node)
            data_store = {}
            
            # Store pin arguments as CodeRange objects (same as other components)
            data_store['pin_a'] = self.get_metadata(PositionProvider, node.args[0].value)
            data_store['pin_b'] = self.get_metadata(PositionProvider, node.args[1].value)
            
            # Store the string values for pin arguments
            data_store['pin_a_value'] = convert_cst_to_str(node.args[0].value)
            data_store['pin_b_value'] = convert_cst_to_str(node.args[1].value)
            
            # Handle optional arguments
            for arg in node.args:
                if arg.keyword:
                    if arg.keyword.value == 'current':
                        port_name = convert_cst_to_str(arg.value).replace("self.", "")
                        port_name = re.sub(r'\[(\d+)]', r':\1', port_name)
                        data_store['current_port_name'] = port_name
                        data_store['current'] = self.get_metadata(PositionProvider, arg.value)
                    elif arg.keyword.value == 'vertices':
                        data_store['vertices'] = self.get_metadata(PositionProvider, arg.value)
            
            # Set default positions for missing optional arguments
            arg_list_end_location = position_of_function.end
            # move the end of the arg list one character to the left,
            # since the function end includes the closing parenthesis,
            # but the last argument should be added _inside_ the parenthesis not after
            arg_list_end_location = CodePosition(line=arg_list_end_location.line, column=arg_list_end_location.column - 1)
            if 'current' not in data_store:
                data_store['current'] = CodeRange(start=arg_list_end_location, end=arg_list_end_location)
                data_store['current_port_name'] = ''
            
            if 'vertices' not in data_store:
                data_store['vertices'] = CodeRange(start=arg_list_end_location, end=arg_list_end_location)
            
            self.subcircuit_instance.arg_position_info[position_of_function.start.line] = data_store


@dataclass
class Pin:
    # Number is a unique identifier
    # It's a str because some chips have "numbers" like "1A" and "1B" such as level shifters
    number: str
    net: str
    parent_uuid: str
    current: float = field(default=0)
    name: str = None  # set automatically to =pin.number if `name` is not set

    def __post_init__(self):
        if self.name is None:
            self.name = self.number

    def __hash__(self):
        return hash((self.parent_uuid, self.number))
        

@dataclass(kw_only=True)
class SchematicComponent:
    circuit: "Circuit"
    uuid: str
    name: str
    ref: str = None
    pins: Dict[tuple[str, str], Pin] = field(default_factory=dict)
    virtual: bool = field(default=False)
    chip: ParsedChip | None = field(default=None)
    
    def __post_init__(self):
        self.circuit.add_part(self)

    def __getitem__(self, key) -> Pin | list[Pin]:
        """
        If indexed with a tuple (name, number) or slice-like syntax [name, number], return the specific matching pin.
        If indexed with a str, first try to find a pin with (name, name) key (for when name==number),
        otherwise return all pins with a matching net name as a list.
        """
        if isinstance(key, tuple) and len(key) == 2:
            pin_key = (str(key[0]), str(key[1]))
            if pin_key in self.pins:
                return self.pins[pin_key]
            raise KeyError(f"No pin found for name={key[0]} and number={key[1]} for chip {self.name}.")
        elif isinstance(key, str):
            matching_pins = [pin for pin in self.pins.values() if pin.name == key]
            if matching_pins:
                return matching_pins
            else:
                raise KeyError(f"No pins found for key {key} for chip {self.name}.")
        
        raise TypeError(f"Pin lookup key must be a str (for net), or (name, number) tuple, not {type(key)}")


@dataclass(kw_only=True)
class SchematicPort(SchematicComponent):
    subcircuit_instance_id: str
    side: Literal['left', 'right']
    y: int
    is_parameter: bool = False
    pins: dict[Tuple[str, str], Pin]

    def __post_init__(self):   
        if not self.pins:
            raise UserFeedback(
                'Error: when calling the Port() function, '
                'pins must be passed as an argument with a non-empty dictionary of pins'
            )

        self.circuit.add_part(self)

    def has_interblock_connection(self):
        connections: List[SvelteFlowEdge] = self.circuit.interblock_connections
        for connection in connections:
            source_handle = connection.sourceHandle.split(':')
            target_handle = connection.targetHandle.split(':')
            # if it's a regular port. source_handle = [component ID, port name]
            # if it's a port group. source_handle = [component ID, port group name, port index]
            if connection.source == self.subcircuit_instance_id and source_handle[1] == self.name:
                return True
            if connection.target == self.subcircuit_instance_id and target_handle[1] == self.name:
                return True
        return False


@dataclass
class Circuit:
    """Represents a real instantiation of a circuit"""
    parts: List[SchematicComponent | SchematicPort] = field(default_factory=list)
    enable_logging: bool = field(default=True)
    _next_net_number: int = field(default=1, init=False, repr=False) 

    def add_part(self, new_part: SchematicComponent):
        if any(hasattr(part, "uuid") and part.uuid == new_part.uuid for part in self.parts):
            raise AttributeError(f"The subcircuit cannot have components with duplicate reference numbers.")
        
        self.parts.append(new_part)

    def bom(self) -> Dict[str, List[BOMEntry]]:
        """Returns the bill of materials for the circuit, grouped by chip ID"""
        bill = defaultdict(list)
        for part in self.parts:
            if part.virtual:
                continue

            chip_id = part.chip.symbol.get_property('LCSC Part')
            if chip_id is None:
                chip_id = part.chip.symbol.get_property('Value')
                
            bill_entry = BOMEntry(
                reference=part.ref,
                value=part.chip.symbol.get_property('Value'),
                datasheet=part.chip.symbol.get_property('Datasheet'),
                footprint=part.chip.symbol.get_property('Footprint'),
                chip_id=chip_id
            )
            
            bill[chip_id].append(bill_entry)

        return bill

    def without_virtual(self) -> "Circuit":
        """
        Return a new Circuit containing only those components
        whose `virtual` attribute is False (or missing).
        """
        new = Circuit(enable_logging=self.enable_logging)

        # populate with only non-virtual components
        for comp in self.parts:
            if not getattr(comp, "virtual", False):
                new.add_part(comp)

        return new

    @property
    def nets(self):
        """
        Construct a dictionary mapping autopcb net names to the pins they connect.

        This function inspects each part and pin in the circuit to collect 
        the net associations based on the 'net' attribute.

        Parameters:
            circuit (Circuit): The circuit object containing parts and pins.

        Returns:
            Dict[str, Set[Pin]]: Dictionary mapping net names to sets of Pin objects.
        """
        nets: Dict[str, Set[Pin]] = {}

        for part in self.parts:
            for pin in part.pins.values():
                # Initialize the set for the net if it hasn't been seen yet
                if pin.net not in nets:
                    nets[pin.net] = set()

                nets[pin.net].add(pin)

        return nets

    def connect_pins(
        self,
        net_a: str, 
        net_b: str
    ):
        if net_a == net_b:
            return

        # Prefer to keep the 'GND' name if one of the nets is GND; otherwise, keep the first one
        net_name_to_keep = net_b if net_b.startswith('GND_') else net_a
        all_nets = self.nets
        combined_net: Set[Pin] = all_nets[net_a] | all_nets[net_b]

        # Reassign all pins to the chosen net name
        for pin in combined_net:
            pin.net = net_name_to_keep

    def next_available_net(self) -> str:
        """
        Generate the next available net name in the format 'NetX'.

        This function produces a new net name each time it is called,
        incrementing an internal counter, regardless of the current state of pins.

        Returns:
            str: The next available net name (e.g., 'Net44').
        """
        net_name = f'Net{self._next_net_number}'
        self._next_net_number += 1
        return net_name

    def high_current_net_name(self, net: str) -> str:
        if net == "GND":
            return "GND"
        current = 0
        for pins_in_net in self.nets[net]:
            current = max(
                current, pins_in_net.current
            )  # todo fixme: when we write our own autorouter, we can use Kirchhoff's law to do much better
        if current <= 0.250:
            return "Signal_" + net
        elif current <= 0.5:
            return "HighCurrent0.5A_" + net
        elif current <= 1:
            return "HighCurrent1A_" + net
        elif current <= 1.5:
            return "HighCurrent1.5A_" + net
        elif current <= 2:
            return "HighCurrent2A_" + net
        elif current <= 2.5:
            return "HighCurrent2.5A_" + net
        elif current <= 3:
            return "HighCurrent3A_" + net
        elif current <= 4:
            return "HighCurrent4A_" + net
        elif current <= 5:
            return "HighCurrent5A_" + net
        else:
            print('Current is too high to route')  
            return net


@dataclass
class Subcircuit:
    """
    Represents a user's subcircuit definition and metadata.

    This model encapsulates both the configuration and state of a subcircuit
    as defined by the user via the frontend. It includes essential details
    for identifying, constructing, and interacting with circuit components
    in a graphical environment such as SvelteFlow.

    Attributes:
        build_is_done (bool): Indicates whether the subcircuit has been built.
            Useful for distinguishing between a constructed and an in-progress node.

        subcircuit_id (str | None): Identifier of the subcircuit that refers to its
            ID in the database

        instance_id (str): A unique identifier assigned by SvelteFlow to this
            specific subcircuit instance (i.e. node or block ID).

        label (str): The human-readable name of the subcircuit. Ex. "Low Side Mosfet"

        name (str): This is the letter prefix of the subcirucit, such as A, B, C, ...
            so chips have unique refs/names in the PCB, like B.U1

        circuit (Circuit): An object representing the circuit.

        user_parameter_values (dict[str, str]): A mapping of user-defined
            parameter keys and their values. These are passed from the frontend
            and control specific behavior/configuration of the subcircuit.

        parameters (dict[str, Parameter]): A dictionary of parameters by name. Each entry
            includes metadata about the parameter (e.g., type, default value, description).
            key: parameter name, value: all the other parameter's info.

        ports (dict[str, PortClass]): A dictionary of ports by name. Each entry
            includes metadata about the port (e.g., direction, connections).
            key: port name, value: all the other port's info.

        store_parsed_info (bool): Flag indicating whether parsed information
            should be retained for introspection or serialization.
    """

    class Config:
        arbitrary_types_allowed = True

    model_config = ConfigDict(
        copy_on_model_validation="none",
        arbitrary_types_allowed=True,
        validate_assignment=True,
    )

    instance_id: str
    label: str
    name: str
    circuit: Circuit
    build_is_done: bool = False
    library_id: str | None = None

    # Variable names are the dictionary keys
    components: Dict[str, Chip | Port | Text | Power | GND | NoConnect | NetLabel] = field(default_factory=dict)
    connections: Dict[str, Connection] = field(default_factory=dict)
    ports: Dict[str, SchematicPort] = field(default_factory=dict) 
    local_chips: Dict[str, ParsedChip] = field(default_factory=dict)

    # User parameter values are the values that the user has set for the parameters in the block diagram
    # which parameters are populated with during subcircuit build
    user_parameter_values: Dict[str, str | int | float | bool] = field(default_factory=dict)
    parameters: dict[str, Parameter] = field(default_factory=dict)

    # Storage for parsed source code information
    arg_position_info: Dict[int, dict] = field(default_factory=dict)
    store_parsed_info: bool = False

    def GND(self, x: int, y: int, rotate: int = 0, reflect: str = ''):
        varname, _ = get_variable_name_current_function_return_is_assigned_to(inspect.stack())
        # Have GND flags be locally connected only within current subcircuit
        # so external GND net connections have to be made explicitly. This is needed when different subcircuits
        # have different ground planes
        part = SchematicComponent(
            circuit=self.circuit,
            name="GND",
            uuid=str(uuid4()),
            virtual=True,
            pins={('1', '1'): Pin(number='1', name='1', net='GND_' + self.instance_id, parent_uuid=varname)}
        )

        if self.store_parsed_info:
            current_frame = inspect.currentframe()
            prev_frame = current_frame.f_back
            _, lineno, _, _, _ = inspect.getframeinfo(prev_frame)
            instantiation_info = self.arg_position_info[lineno]
            self.local_chips['GND'] = ParsedChip(symbol=GNDSymbol("GND"))
            self.components[varname] = (
                GND(
                    varname=ArgInfoVar(value=varname, position=instantiation_info['varname']), 
                    chip_id=ArgInfoStr(value="GND", position=DEFAULT_CODE_RANGE),
                    x=ArgInfoInt(value=x, position=instantiation_info['x']),
                    y=ArgInfoInt(value=y, position=instantiation_info['y']),
                    rotate=ArgInfoInt(value=rotate, position=instantiation_info['rotate']),
                    reflect=ArgInfoStr(value=reflect, position=instantiation_info['reflect']),
                )
            )

        return part

    def Power(self, name: str, *, x: int, y: int, rotate: int = 0, reflect: str = ''):
        varname, _ = get_variable_name_current_function_return_is_assigned_to(inspect.stack())
        part = SchematicComponent(
            circuit=self.circuit,
            name=f"VCC_{name}", 
            uuid=str(uuid4()),
            virtual=True,
            # add instance id to the net name to make the net local to the current subcirucit
            pins={('1', '1'): Pin(number='1', name='1', net=name + self.instance_id, parent_uuid=varname)}
        )

        if self.store_parsed_info:
            current_frame = inspect.currentframe()
            prev_frame = current_frame.f_back
            _, lineno, _, _, _ = inspect.getframeinfo(prev_frame)
            instantiation_info = self.arg_position_info[lineno]
            self.local_chips['VCC'] = ParsedChip(symbol=PowerSymbol(name))
            self.components[varname] = (
                Power(
                    varname=ArgInfoVar(value=varname, position=instantiation_info['varname']), 
                    chip_id=ArgInfoStr(value='VCC', position=DEFAULT_CODE_RANGE),
                    name=ArgInfoStr(value=name, position=instantiation_info['name'], gui=ArgInfoGuiOptions(visible=True, editable=True)),
                    x=ArgInfoInt(value=x, position=instantiation_info['x']),
                    y=ArgInfoInt(value=y, position=instantiation_info['y']),
                    rotate=ArgInfoInt(value=rotate, position=instantiation_info['rotate']),
                    reflect=ArgInfoStr(value=reflect, position=instantiation_info['reflect']),
                )
            )

        return part

    def Text(self, content: str, *, x: int, y: int, size: int = 8):
        """Add a free text component to subcircuit"""
        varname, _ = get_variable_name_current_function_return_is_assigned_to(inspect.stack())
        if self.store_parsed_info:
            current_frame = inspect.currentframe()
            prev_frame = current_frame.f_back
            _, lineno, _, _, _ = inspect.getframeinfo(prev_frame)
            instantiation_info = self.arg_position_info[lineno]
            self.components[varname] = (
                Text(
                    varname=ArgInfoVar(value=varname, position=instantiation_info['varname']), 
                    content=ArgInfoStr(value=content, position=instantiation_info['content'], gui=ArgInfoGuiOptions(visible=True, editable=True)),
                    size=ArgInfoInt(value=size, position=instantiation_info['size'], gui=ArgInfoGuiOptions(visible=True, editable=True)),
                    x=ArgInfoInt(value=x, position=instantiation_info['x']),
                    y=ArgInfoInt(value=y, position=instantiation_info['y']),
                )
            )

    def Parameter(self, default: bool | int | float | str, choices: list[str] | None = None, description: str = ""):
        parameter_name, _ = get_variable_name_current_function_return_is_assigned_to(inspect.stack())
        if parameter_name in self.parameters:
            raise UserFeedback(f"Parameter with a name {parameter_name} has already been declared.")

        if choices is not None:
            if default is not None and default not in choices:
                raise UserFeedback(f"The default value {default} is not in the choices {choices}")
            elif default is None and len(choices) > 0:
                default = choices[0]
        current_value = self.user_parameter_values.get(parameter_name, default)

        if self.store_parsed_info:
            current_frame = inspect.currentframe()
            prev_frame = current_frame.f_back
            _, lineno, _, _, _ = inspect.getframeinfo(prev_frame)
            instantiation_info = self.arg_position_info[lineno]
        else:
            instantiation_info = dict()

        if type(default) is str:
            default_value_arg_metadata_class = ArgInfoStr
        elif type(default) is bool:
            default_value_arg_metadata_class = ArgInfoBool
        elif type(default) is int:
            default_value_arg_metadata_class = ArgInfoInt
        elif type(default) is float:
            default_value_arg_metadata_class = ArgInfoFloat

        self.parameters[parameter_name] = (
            # todo fixme: using .get with the fallback of DEFAULT_CODE_RANGE is a bad idea
            # it's a workaround because we need the full position info in the subcircuit editor,
            # but we don't need the source code position info in the block diagram editor when building the PCB
            # so the code positions are not known, and in all the other subcircuit components, we store the critical
            # info needed for the block diagram in another duplicate object (ex. ports has Subcircuit.ports for
            # the block diagram, and .components that contains the same info with the source code positions)
            # we should think of a better long term solution

            Parameter(
                varname=ArgInfoVar(value=parameter_name, position=instantiation_info.get('varname', DEFAULT_CODE_RANGE)),
                current_value=current_value,
                default=default_value_arg_metadata_class(value=default, position=instantiation_info.get('default', DEFAULT_CODE_RANGE)),
                choices=ArgInfoArray(value=choices, position=instantiation_info.get("choices", DEFAULT_CODE_RANGE), gui=ArgInfoGuiOptions(visible=True, editable=True)) if choices is not None else None,
                description=ArgInfoStr(value=description, position=instantiation_info.get("description", DEFAULT_CODE_RANGE))
            )
        )

        return current_value

    def Port(self, side: Literal['left', 'right'], y: int, pins: List[str]):
        if not isinstance(pins, list):
            raise UserFeedback(f"The pins argument must be a list of the pin names. It is currently a {type(pins)}")
        if len(pins) == 0:
            raise UserFeedback(f"An empty list was given for the names of pins. The pins argument must contain a non-empty list of pin names.")
        if len(pins) != len(set(pins)):
            raise UserFeedback(f'Duplicate pin names not allowed: {pins}')
       
        port_name, _ = get_variable_name_current_function_return_is_assigned_to(inspect.stack())
       
        if port_name in self.ports:
            raise UserFeedback(f"Port with a name {port_name} has already been declared.")

        # Construct the pin dictionary
        pin_dict = {
            (pin_name, pin_name): Pin(
                number=pin_name, name=pin_name, net=self.circuit.next_available_net(), parent_uuid=port_name
            )
            for pin_name in pins
        }
        
        port = SchematicPort(
            circuit=self.circuit, 
            subcircuit_instance_id=self.instance_id,
            name=port_name, 
            uuid=str(uuid4()),
            y=y,
            pins=pin_dict,
            side=side,
            virtual=True
        )
        self.ports[port_name] = port

        if len(pins) > 10:
            raise UserFeedback(
                f"Currently ports with more than 10 connections are not supported."
                f" This currently has {len(pins)} connections"
            )

        if self.store_parsed_info:
            current_frame = inspect.currentframe()
            prev_frame = current_frame.f_back
            _, lineno, _, _, _ = inspect.getframeinfo(prev_frame)
            instantiation_info = self.arg_position_info[lineno]

            response = http_request("get", f"/chips/?chip_id={quote('JLC/C49240' + str(len(pins) - 1))}")
            chip = ParsedChip.from_json(response.content)   
            # deep copy it because we'll be modifying the pin names,
            # and other ports might use the same symbol
            chip = copy.deepcopy(chip)
            chip.symbol.name = f"port-{port_name}-C49240{len(pins) - 1}"
            for i, pin in enumerate(chip.symbol.pinlist()):
                pin_name = pins[i]
                pin.number.number = pin_name
                pin.name.name = pin_name
            
            self.local_chips[chip.symbol.name] = chip
            self.components[port_name] = (
                Port(
                    varname=ArgInfoVar(value=port_name, position=instantiation_info['varname']),
                    chip_id=ArgInfoStr(value=chip.symbol.name, position=DEFAULT_CODE_RANGE),
                    side=ArgInfoChoice(value=side, position=instantiation_info["side"], gui=ArgInfoGuiOptions(visible=True, editable=True, choices=['left', 'right'])),
                    pins=ArgInfoArray(value=pins, position=instantiation_info["pins"], gui=ArgInfoGuiOptions(visible=True, editable=True)),
                    x=ArgInfoInt(value=0, position=DEFAULT_CODE_RANGE),
                    y=ArgInfoInt(value=y, position=instantiation_info["y"]),
                )
            )

        return port

    def Part(
        self,
        chip_id: str,
        x: int,
        y: int,
        rotate: int = 0,
        reflect: str = '',
        unit: int = 1,
        variant: int = 1,
        ref_position: str = 'top',
        **kwargs
    ) -> Chip:
        raw_chip_id = chip_id
        chip = None

        if local_chip := self.local_chips.get(chip_id):
            # If chip was added via gui it should already be in local_chips
            chip = local_chip
        elif subcategory := is_parametric_chip(chip_id):
            filters_json = json.dumps(kwargs)
            encoded_filters = quote(filters_json)

            # Build search URL with supplier parameter
            supplier, subcategory_name = chip_id.split("/")
            category_id_param = subcategory.get('category_id', subcategory_name)
            result = http_request("get", f"/chips/search?supplier={supplier.lower()}&category_id={category_id_param}&filters={encoded_filters}")
            if result.status_code == 404:
                raise UserFeedback("Could not find a part with provided filters.")
            if result.status_code == 503:
                raise UserFeedback("Chip API of provided supplier is currently unavailable. Cannot resolve parametric chip. Please try again later.")
            
            search_results = json.loads(result.content) if result.content != '' else None
            if not search_results or len(search_results) == 0:
                raise UserFeedback("Could not find a part with provided filters.")

            first_result = search_results[0]
            chip = ParsedChip(
                symbol=LibSymbol.from_dict(first_result['symbol']),
                footprint=Footprint.from_dict(first_result['footprint']) if first_result.get('footprint') else None
            )
            chip_id = f"{supplier}/{first_result['uid']}"  # the lcsc C id
        else:
            # Chip ID is specified directly, but hasn't been fetched yet
            result = http_request("get", f"/chips/?chip_id={quote(chip_id)}")
            chip = ParsedChip.from_json(result.content)

        if chip is None:
            raise UserFeedback("Requested part not found.")

        ref, _ = get_variable_name_current_function_return_is_assigned_to(inspect.stack())
        part_uuid = generate_footprint_uuid(ref, self.instance_id)

        # Enforce ref format and handle unit groups for chips with multiple units
        if chip.symbol.has_multiple_units():
            match = re.match(r"([A-Za-z0-9]+)([A-Z])$", ref)
            if not match:
                raise UserFeedback(
                    f"Reference '{ref}' for a multi-unit chip must be in the form <alphanumerical prefix><one capital letter>, e.g., 'U1A'."
                )
            unit_group_name = match.group(1)

            # Check if a parent chip for this subunit already exists in the circuit
            existing_part = None
            for part in self.circuit.parts:
                if (
                    isinstance(part, SchematicComponent)
                    and getattr(part, "ref", None) == f"{self.name}.{unit_group_name}"
                ):
                    existing_part = part
                    break

            unit_pins = {(pin.name.name, pin.number.number): Pin(parent_uuid=ref, number=pin.number.number, name=pin.name.name, net=self.circuit.next_available_net()) for pin in chip.symbol.pinlist(unit=unit, variant=variant)}

            if existing_part is not None:
                part = existing_part
                # Hydrate the part with the pins for this unit symbol
                part.pins.update(unit_pins)
            else:
                # If the parent chip of this unit doesn't exist yet, instantiate a new chip
                # Use a symbol group uuid instead of unit uuid 
                part = SchematicComponent(
                    circuit=self.circuit,
                    chip=chip,
                    name=chip.symbol.name,
                    uuid=generate_footprint_uuid(unit_group_name, self.instance_id),
                    ref=f"{self.name}.{unit_group_name}",
                    pins=unit_pins
                )
        else:
            part_uuid = generate_footprint_uuid(ref, self.instance_id)
            part = SchematicComponent(
                circuit=self.circuit,
                chip=chip,
                name=chip.symbol.name,
                uuid=part_uuid,
                ref=f"{self.name}.{ref}",
                pins={(pin.name.name, pin.number.number): Pin(parent_uuid=ref, number=pin.number.number, name=pin.name.name, net=self.circuit.next_available_net()) for pin in chip.symbol.pinlist()}
            )

        if self.store_parsed_info:
            current_frame = inspect.currentframe()
            prev_frame = current_frame.f_back
            _, lineno, _, _, _ = inspect.getframeinfo(prev_frame)
            instantiation_info = self.arg_position_info[lineno]
            self.local_chips[chip_id] = chip

            datasheet = chip.symbol.get_property('Datasheet', '')
            mpn = chip.symbol.get_property('Value')

            component = (
                Chip(
                    varname=ArgInfoVar(value=ref, position=instantiation_info['varname']),
                    chip_id=ArgInfoStr(value=chip_id, position=instantiation_info['chip_id'], gui=ArgInfoGuiOptions(visible=True, editable=False)),
                    unit=ArgInfoChoice(value=unit, position=instantiation_info['unit'], gui=ArgInfoGuiOptions(visible=chip.symbol.has_multiple_units(), editable=True,
                                 choices=[unit._unit for unit in chip.symbol.symbols if unit._unit != 0]  # leave out unit 0 since it's common to all subunits
                              )),
                    # todo fixme implement variant choices the same way unit choices is implemented
                    variant=ArgInfoChoice(value=variant, position=instantiation_info['variant'], gui=ArgInfoGuiOptions(visible=False, editable=True, choices=[1])),
                    x=ArgInfoInt(value=x, position=instantiation_info['x']),
                    y=ArgInfoInt(value=y, position=instantiation_info['y']),
                    rotate=ArgInfoInt(value=rotate, position=instantiation_info['rotate']),
                    reflect=ArgInfoStr(value=reflect, position=instantiation_info['reflect']),
                    datasheet=ArgInfoUrl(value=datasheet, position=DEFAULT_CODE_RANGE, gui=ArgInfoGuiOptions(visible=True, editable=False)),
                    mpn=ArgInfoStr(value=mpn, position=DEFAULT_CODE_RANGE, gui=ArgInfoGuiOptions(visible=True, editable=False)),
                    ref_position=ArgInfoChoice(value=ref_position, position=instantiation_info['ref_position'], gui=ArgInfoGuiOptions(visible=True, editable=True, choices=['top', 'top_right', 'top_left', 'left', 'right', 'bottom', 'bottom_left', 'bottom_right']))
                )
            )

            if is_parametric_chip(raw_chip_id):
                component = component.asdict()
                component['category'] = ArgInfoChoice(
                    value=raw_chip_id,
                    position=instantiation_info['chip_id'],
                    gui=ArgInfoGuiOptions(visible=True, editable=True)
                )
                for k, v in kwargs.items():
                    # Skip internal metadata fields
                    if k.startswith('_'):
                        continue
                    gui = ArgInfoGuiOptions(visible=True, editable=True, is_filter=True)
                    position = instantiation_info[k]
                    if type(v) is list:
                        component[k] = ArgInfoMultiChoice(value=v, position=position, gui=gui)
                    elif type(v) is str:
                        component[k] = ArgInfoPhysicalUnitRange(value=v, position=position, gui=gui)
                    else:
                        raise UserFeedback(f"Invalid value type for filter {k}: {type(v)}")

            try:
                if first_result['datasheet'] is not None:
                    component['datasheet'] = ArgInfoUrl(value=first_result['datasheet'], position=DEFAULT_CODE_RANGE, gui=ArgInfoGuiOptions(visible=True, editable=False))
                if first_result['package'] is not None:
                    component['package'] = ArgInfoStr(value=first_result['package'], position=DEFAULT_CODE_RANGE, gui=ArgInfoGuiOptions(visible=True, editable=False))
                if first_result['description'] is not None:
                    component['description'] = ArgInfoStr(value=first_result['description'], position=DEFAULT_CODE_RANGE, gui=ArgInfoGuiOptions(visible=True, editable=False))
            except (NameError, KeyError):
                # `first_result` is only defined if it's a parametric chip,
                # and it's only set for JLC parts as of now
                # Eventually we should add these attributes for the rest
                # of the sources of chips as well
                pass

            self.components[ref] = component

        return part
    
    def NoConnect(self, x: int, y: int):
        """Adds a no connect flag that can be attached to a pin"""
        name, _ = get_variable_name_current_function_return_is_assigned_to(inspect.stack())
        noconnect = SchematicComponent(
            circuit=self.circuit,
            name="NoConnect", 
            uuid=str(uuid4()),
            virtual=True,
            # generate a globally unique net name so the NoConnect symbol's pin is on it's own unique net
            # and not connected to anything else.
            pins={('1', '1'): Pin(number='1', name='1', net=self.circuit.next_available_net(), parent_uuid=name)}
        )

        if self.store_parsed_info:
            current_frame = inspect.currentframe()
            prev_frame = current_frame.f_back
            _, lineno, _, _, _ = inspect.getframeinfo(prev_frame)
            instantiation_info = self.arg_position_info[lineno]
            self.local_chips['NoConnect'] = ParsedChip(symbol=NoConnectSymbol(name))
            self.components[name] = (
                NoConnect(
                    varname=ArgInfoVar(value=name, position=instantiation_info['varname']),
                    chip_id=ArgInfoStr(value='NoConnect', position=DEFAULT_CODE_RANGE),
                    x=ArgInfoInt(value=x, position=instantiation_info["x"]),
                    y=ArgInfoInt(value=y, position=instantiation_info["y"]),
                )
            )
        
        return noconnect
    
    def NetLabel(
        self, 
        net: str, 
        *,
        x: int,
        y: int,
        rotate: int = 0,
        reflect: str = '',
    ):
        """Adds a net label to the subcircuit"""
        name, _ = get_variable_name_current_function_return_is_assigned_to(inspect.stack())
        netlabel = SchematicComponent(
            circuit=self.circuit,
            virtual=True,
            name=name,
            uuid=str(uuid4()),
            pins={'1': Pin(parent_uuid=name, number='1', net=net + self.instance_id)}
        )

        if self.store_parsed_info:
            current_frame = inspect.currentframe()
            prev_frame = current_frame.f_back
            _, lineno, _, _, _ = inspect.getframeinfo(prev_frame)
            instantiation_info = self.arg_position_info[lineno]
            self.local_chips[f"NetLabel-{net}"] = ParsedChip(symbol=NetLabelSymbol(net))
            self.components[name] = (
                NetLabel(
                    varname=ArgInfoVar(value=name, position=instantiation_info["varname"]),
                    chip_id=ArgInfoStr(value=f"NetLabel-{net}", position=DEFAULT_CODE_RANGE),         
                    net=ArgInfoStr(value=net, position=instantiation_info["net"], gui=ArgInfoGuiOptions(visible=True, editable=True)),
                    x=ArgInfoInt(value=x, position=instantiation_info["x"]),
                    y=ArgInfoInt(value=y, position=instantiation_info["y"]),
                    rotate=ArgInfoInt(value=rotate, position=instantiation_info['rotate']),
                    reflect=ArgInfoStr(value=reflect, position=instantiation_info['reflect']),
                )
            )

        return netlabel

    def connect(
        self,
        pins_a: Pin | List[Pin],
        pins_b: Pin | List[Pin],
        /,
        *,
        vertices: List[Tuple[int, int]] | None = None,
        current: SchematicPort | float = 0,
    ):
        """
        Connects multiple input pins to a target pin (of a Part object).
        The optional vertices argument is a list of tuples for any vertices of bends in the connection line between the pins when drawing the schematic
        The start and end points of the connection line are the pins locations, so if no vertices argument is given, it will just be a straight line

        Args:
            pins_a (Pin | List[Pin]): Origin pins to start the connection from
            pins_b (Pin | List[Pin]): Target pins to connect to from origin pins (right now list not supported)
            vertices (List[Tuple[int, int]]): List of tuples for any vertices of bends in the connection line
            current (Port): Current flowing through the connection (equal to external supply from a specified port)
        """
        # If vertices arg is passed, make sure there are no duplicate vertices,
        # as it breaks our rendering algorithm for terminating connections on other connections
        # (rather than terminating on a pin)
        if vertices is not None and len(vertices) != len(set(vertices)):
            raise UserFeedback(f'Duplicate vertices with the same coordinates not allowed: vertices = {vertices}')
        
        connection_current = current
        if isinstance(current, SchematicPort):
            try:
                interblock_connections: list[SvelteFlowEdge] = self.circuit.interblock_connections
            except AttributeError:
                # If we're opening in the subcircuit editor, there are no interblock connection
                interblock_connections = []

            connection_current = sum(
                [
                    conn.data.current
                    for conn in interblock_connections
                    if (
                        (conn.source == current.subcircuit_instance_id and conn.sourceHandle.split(':')[1] == current.name)
                        or (
                            conn.target == current.subcircuit_instance_id
                            and conn.targetHandle.split(':')[1] == current.name
                        )
                    )
                ]
            )

            self.ports[current.name].is_parameter = True

        def is_valid_input_to_connect_pins(pins):
            if isinstance(pins, list):
                return all([isinstance(pin, Pin) for pin in pins])
            elif isinstance(pins, Pin):
                return True
            else:
                return False

        if pins_a == pins_b and vertices is not None and len(vertices) == 0:
            raise UserFeedback(
                f'The inputs pins are exactly the same. They must be different to establish a valid connection,'
                f'or at least one vertex has to be added so the length of the connection is not 0.'
            )

        if not is_valid_input_to_connect_pins(pins_a) or not is_valid_input_to_connect_pins(pins_b):
            raise UserFeedback(
                f'The first two inputs to self.connect_pins() must be either a Pin or a list of Pin. '
                f'They are currently of type "{type(pins_a)}" and "{type(pins_b)}"'
            )

        # Simplify [one element] list of Pins
        if isinstance(pins_a, list) and len(pins_a) == 1:
            pins_a = pins_a[0]
        if isinstance(pins_b, list) and len(pins_b) == 1:
            pins_b = pins_b[0]

        # If a one-to-many
        # to reduce repeated code, make sure that if one is a list and the other is not
        # make b the list and a the single pin
        if isinstance(pins_a, list) and not isinstance(pins_b, list):
            pins_a, pins_b = pins_b, pins_a

        # If a many-to-many connection
        if isinstance(pins_a, list) and isinstance(pins_b, list):
            raise UserFeedback('This is not supported yet')
            # When it is supported, it will look something like this
            # if len(pins_a) != len(pins_b):
            #     raise UserFeedback(f'The number of pins in each argument of self.connect_pins need to match. '
            #                        f'Currently they have {len(pins_a)} and {len(pins_b)}')
            # for i in range(len(pins_a)):
            #     pins_a[i] += pins_b[i]

        # If a one-to-one connection
        elif not isinstance(pins_a, list) and not isinstance(pins_b, list):
            self.circuit.connect_pins(pins_a.net, pins_b.net)
            pins_a.current = max(connection_current, pins_a.current)
            pins_b.current = max(connection_current, pins_b.current)
        elif not isinstance(pins_a, list) and isinstance(pins_b, list):
            # If a one-to-many connection (never a many-to-one, since we checked above)
            for other_pin in pins_b:
                self.circuit.connect_pins(pins_a.net, other_pin.net)
                other_pin.current = max(connection_current, other_pin.current)
            pins_a.current = max(connection_current, pins_a.current)
        else:
            raise Exception(
                f'The inputs to connect_pins are unrecognized. They are of type {type(pins_a)} and {type(pins_b)}'
            )

        if self.store_parsed_info:
            current_frame = inspect.currentframe()
            prev_frame = current_frame.f_back
            _, lineno, _, _, _ = inspect.getframeinfo(prev_frame)
            # If it's a pin, put it in a list to keep the code below the same
            if not isinstance(pins_b, list):
                pins_b = [pins_b]
            for pin in pins_b:
                if isinstance(current, SchematicPort):
                    current_arg_value = self.arg_position_info[lineno]['current_port_name']
                else:
                    current_arg_value = connection_current

                connection_uuid = str(uuid4())
                
                # Store connection in self.connections (standard location)
                self.connections[connection_uuid] = Connection(
                    parent_component_a_uuid=pins_a.parent_uuid,
                    parent_component_b_uuid=pin.parent_uuid,
                    pid_a=PinId(name=pins_a.name, number=pins_a.number),
                    pid_b=PinId(name=pin.name, number=pin.number),
                    uuid=connection_uuid,
                    pin_a=ArgInfoChoice(value=self.arg_position_info[lineno]['pin_a_value'], position=self.arg_position_info[lineno]['pin_a'], gui=ArgInfoGuiOptions(visible=False, editable=True, choices=[])),
                    pin_b=ArgInfoChoice(value=self.arg_position_info[lineno]['pin_b_value'], position=self.arg_position_info[lineno]['pin_b'], gui=ArgInfoGuiOptions(visible=False, editable=True, choices=[])),
                    vertices=ArgInfoArray(value=vertices if vertices is not None else [], position=self.arg_position_info[lineno]['vertices'], gui=ArgInfoGuiOptions(visible=False, editable=True, choices=[])),
                    current=ArgInfoChoice(value=str(current_arg_value) if current != 0 else '', position=self.arg_position_info[lineno]['current'], gui=ArgInfoGuiOptions(visible=True, editable=True, choices=list(self.ports.keys()))),
                )


# To run locally (mainly for debugging)
# in the working directory backend/ run python -m autopcb.core
if __name__ == "__main__":
    from gql import Client, gql
    from gql.transport.aiohttp import AIOHTTPTransport
    from pydantic_settings import BaseSettings

    class Settings(BaseSettings):
        hasura_admin_secret: str
        HASURA_ENDPOINT: str

        class Config:
            extra = "allow"

    settings = Settings(_env_file='.env')

    transport = AIOHTTPTransport(
        url=settings.HASURA_ENDPOINT,
        headers={'X-Hasura-Admin-Secret': settings.hasura_admin_secret},
    )
    client = Client(transport=transport, fetch_schema_from_transport=True)

    subcircuit_to_build_id = 'b6898cdf-fee2-4803-8b1c-2b649b525559'
    query = gql(
        f"""
        query GetLatestFileVersion {{
            file_versions(
                order_by: {{ version_timestamp: desc }}
                limit: 1
                where: {{ file_id: {{ _eq: "{subcircuit_to_build_id}" }} }}
            ) {{
                file_id
                file_content
                file_name
                category
                description
                version_timestamp
            }}
        }}
        """)
    result = client.execute(query)
    subcircuitMetadata = result['file_versions'][0]

    Path("subcircuits").mkdir(exist_ok=True)
    subcircuit_path = Path(f"subcircuits/{subcircuitMetadata['file_id']}.py")
    if not subcircuit_path.exists() or subcircuit_path.read_text() != subcircuitMetadata['file_content']['python_source_code']:
        # don't rewrite the file if it already exists with the file contents,
        # to not trigger hot reloading of backend when doing development / debuggeng
        subcircuit_path.write_text(subcircuitMetadata['file_content']['python_source_code'])
    raw_subcircuit = RawSubcircuit.from_dict({
        'file_name': subcircuitMetadata['file_name'],
        'file_id': subcircuitMetadata['file_id'],
        'python_source_code': subcircuitMetadata['file_content']['python_source_code'],
        'chips': subcircuitMetadata['file_content']['parsed']['chips'],
        'user_parameter_values': {},
    })
    parsed_subcircuit = parse_subcircuit(raw_subcircuit)
    quit()

    # Copy this from the URL in the app

    # todo fixme run profiler to make this faster
    file_id_to_build = '9c995ee2-11b4-4daf-9c85-698064b75e5c'
    query = gql(
        f"""
        query GetLatestFileVersion {{
            file_versions(
                where: {{ file_id: {{ _eq: "{file_id_to_build}" }} }}
                order_by: {{ version_timestamp: desc }}
                limit: 1
            ) {{
                file_id
                file_name
                description
                category
                version_timestamp
                file_content
            }}
    }}
    """)

    result = client.execute(query)
    blockDiagram = result['file_versions'][0]
    block_diagram_svelteflow_json = result['file_versions'][0]['file_content']['block_diagram_svelteflow_json']
    subcircuitIds = map(lambda node: node['data']['subcircuit_info']['subcircuit_id'], block_diagram_svelteflow_json['nodes'])
    query = gql(f"""query GetFiles {{
    file_versions(
        where: {{ file_id: {{ _in: ["{'","'.join(subcircuitIds)}"] }} }}
        order_by: [{{ file_id: asc }}, {{ version_timestamp: desc }}]
        distinct_on: file_id
    ) {{
        file_id
        file_content
    }}
    }}
""")
    print(query)
    result = client.execute(query)


    Path("subcircuits").mkdir(exist_ok=True)
    # Write each subcircuit to a file, so they can be imported by python
    for subcircuit in result['file_versions']:
        library_id = subcircuit['file_id']
        code = subcircuit['file_content']['python_source_code']
        subcircuit_path = Path(f"subcircuits/{library_id}.py")
        if not subcircuit_path.exists() or subcircuit_path.read_text() != code:
            # don't rewrite the file if it already exists with the file contents,
            # to not trigger hot reloading of backend when doing development / debugging
            subcircuit_path.write_text(code)

    from .io import generate_pcb
    pcbInput = {'blockDiagram': blockDiagram,
                'subcircuits': {subcircuit['file_id']: {'chips':subcircuit['file_content']['python_source_code']} for subcircuit in result['file_versions']}}
    block_diagram = BlockDiagram.from_dict(pcbInput['blockDiagram'])
    result = generate_pcb(block_diagram, pcbInput['subcircuits'])
    Path('/tmp/out.kicad_pcb').write_text(result.pcb.kicad_pcb)
    print(result.json())
    quit()

    # remove the subcircuits directory because if it's left over
    # so it doesn't get zipped up and sent to the frontend since the
    # whole autopcb folder is sent
    import shutil
    shutil.rmtree('subcircuits')


    # Demo of autopcb.core library functions used by the frontend js via pyodide
    # print(get_subcircuit_port_info(mcu_subcircuit_in_file))
    print(get_last_line_of_subcircuit_source_code(mcu_subcircuit_in_file))

    node = [node for node in nodes if node.data.subcircuit_info.subcircuit_id == mcu_subcircuit_in_file][0]
    library_id = node.data.subcircuit_info.subcircuit_id
    subcircuit_name = node.data.subcircuit_info.name
    subcircuit_module = importlib.import_module("subcircuits." + library_id)
    # todo fixme only run the following reload if it's really needed (file changed)
    importlib.reload(subcircuit_module)
    subcircuit_subclass: type[Subcircuit] = subcircuit_module.__getattribute__(subcircuit_name)
    circuit = Circuit()
    mcu_subcircuit_instance = subcircuit_subclass(
        circuit=circuit,
        instance_id=node.id,
        library_id=library_id,
        name='TEST SUBCIRCUIT',
        label=subcircuit_subclass.__name__,
        user_parameter_values=node.data.params
    )
    print(get_block_diagram_node_info(mcu_subcircuit_instance))