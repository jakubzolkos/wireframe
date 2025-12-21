from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
import math
import re
import sys
import time
from typing import Any, List, Optional, Set, Union, Dict, Tuple

from autopcb.utils import generate_alphabetical_suffix, kicad_to_autopcb_units
from autopcb.datatypes.common import Vector2D, Vector2DWithRotation
from autopcb.datatypes.mixins import SexprMixin, DataclassSerializerMixin
from autopcb.exceptions import MissingSchematicSymbolException

from .fields import positional, flag_boolean
from autopcb.datatypes.common import Margins


@dataclass
class PinLoc:
    """A single pin (logical endpoint) in the schematic."""
    symbol_inst: "SchSymbol"         
    pin: "Pin"                             
    pos: Vector2DWithRotation


@dataclass
class SchematicSymbolMetadata:
    footprint: str | None
    lcsc_part: str | None
    reference: str | None
    value: str | None
    datasheet: str | None


Point = Tuple[float, float]


@dataclass
class Edge:
    other_node: Point
    distance: float


@dataclass(kw_only=True)
class SchFont:
    face: Optional[str]
    size: Optional[Vector2D]
    thickness: Optional[float]
    bold: Optional[bool]
    italic: Optional[bool]
    color: Optional[Tuple[int, int, int, float]]
    line_spacing: Optional[float]


@dataclass(kw_only=True)
class SchEffects:
    font: Optional[SchFont]
    justifies: List[str]
    href: Optional[str]
    hide: Optional[bool]


@dataclass
class Color:
    r: int = positional()  # 255
    g: int = positional()
    b: int = positional()
    a: float = positional()  # 0-1


@dataclass(kw_only=True)
class SchStroke:
    width: float
    type: str = "default"
    color: Optional[Color]


@dataclass(kw_only=True)
class Fill:
    type: str = "none"
    color: Optional[Color]


@dataclass(kw_only=True)
class SchPageInfo:
    type: str = positional()
    width: Optional[float] = positional()
    height: Optional[float] = positional()
    portrait: bool = flag_boolean()


@dataclass
class SchTitleBlockComment:
    index: int = positional()
    text: str = positional()


@dataclass(kw_only=True)
class SchTitleBlock:
    title: Optional[str]
    date: Optional[str]
    rev: Optional[str]
    company: Optional[str]
    comments: List[SchTitleBlockComment]


@dataclass(kw_only=True)
class SchShapeLineChain:
    xys: List[Vector2D]


@dataclass(kw_only=True)
class PinNames:
    offset: Optional[float]
    hide: Optional[bool]


@dataclass(kw_only=True)
class PinNumbers:
    hide: Optional[bool]


@dataclass(kw_only=True)
class SchProperty:
    name: str = positional()
    value: str = positional()
    private: bool = flag_boolean()
    id: Optional[int]
    at: Vector2DWithRotation
    hide: Optional[bool]
    effects: Optional[SchEffects]
    show_name: Optional[bool]
    do_not_autoplace: Optional[bool]


@dataclass(kw_only=True)
class PinAlternate:
    name: str = positional()
    type: str = positional()
    shape: str = positional()


@dataclass(kw_only=True)
class PinName:
    name: str = positional()
    effects: Optional[SchEffects]


@dataclass(kw_only=True)
class PinNumber:
    number: str = positional()  # yes, this is a str
    effects: Optional[SchEffects]


@dataclass(kw_only=True)
class Pin:
    type: str = positional()
    shape: str = positional()
    at: Optional[Vector2DWithRotation]
    length: float
    hide: bool
    name: Optional[PinName]
    number: Optional[PinNumber]
    alternates: List[PinAlternate]
    uuid: Optional[str]


@dataclass(kw_only=True)
class ArcShape:
    private: bool = flag_boolean()
    start: Vector2D
    mid: Vector2D
    end: Vector2D
    radius: Optional[Tuple[Vector2D, float, Tuple[float, float]]]
    stroke: Optional[SchStroke]
    fill: Optional[Fill]


@dataclass(kw_only=True)
class Bezier:
    private: bool = flag_boolean()
    pts: SchShapeLineChain
    stroke: Optional[SchStroke]
    fill: Optional[Fill]


@dataclass(kw_only=True)
class Circle:
    private: bool = flag_boolean()
    center: Vector2D
    radius: float
    stroke: Optional[SchStroke]
    fill: Optional[Fill]


@dataclass(kw_only=True)
class Polyline:
    private: bool = flag_boolean()
    pts: Optional[SchShapeLineChain]
    stroke: Optional[SchStroke]
    fill: Optional[Fill]


@dataclass(kw_only=True)
class Rectangle:
    private: bool = flag_boolean()
    start: Vector2D
    end: Vector2D
    radius: Optional[float]
    stroke: Optional[SchStroke]
    fill: Optional[Fill]


@dataclass(kw_only=True)
class SchFreeformText:
    text: str = positional()
    private: bool = flag_boolean()
    at: Vector2DWithRotation
    effects: Optional[SchEffects]


@dataclass(kw_only=True)
class SchTextBox:
    text: str = positional()
    exclude_from_sim: Optional[bool]
    at: Vector2DWithRotation
    size: Vector2D
    margins: Optional[Margins]
    stroke: Optional[SchStroke]
    fill: Optional[Fill]
    effects: Optional[SchEffects]
    uuid: Optional[str]

    
@dataclass(kw_only=True)
class SymbolUnit: 
    name: str = positional()
    unit_name: Optional[str]
    polylines: List[Polyline]
    arcs: List[ArcShape]
    beziers: List[Bezier]
    circles: List[Circle]
    rectangles: List[Rectangle]
    texts: List[SchFreeformText]
    text_boxes: List[SchTextBox]
    pins: List[Pin]
    _unit: int = None
    _variant: int = None

    def __post_init__(self):
        """Sets the unit and variant ID's of the symbol unit. KiCAD defines unit name as ``<symbolName>_<unit>_<variant>``
        """
        parse_symbol_id = re.match(r"^(.+?)_(\d+?)_(\d+?)$", self.name)
        if parse_symbol_id:
            self._unit = int(parse_symbol_id.group(2))
            self._variant = int(parse_symbol_id.group(3))


@dataclass(kw_only=True)
class BodyStyles:
    demorgan: bool = flag_boolean()
    names: List[str]


@dataclass(kw_only=True)
class SchEmbeddedFile:
    name: str
    data: str
    type: Optional[str]


@dataclass
class PowerFlag:
    pass


@dataclass(kw_only=True)
class LibSymbol(DataclassSerializerMixin):
    name: str = positional()
    power: Optional[PowerFlag]
    body_styles: Optional[BodyStyles]
    pin_numbers: Optional[PinNumbers]
    pin_names: Optional[PinNames]
    exclude_from_sim: Optional[bool]
    in_bom: Optional[bool]
    on_board: Optional[bool]
    duplicate_pin_numbers_are_jumpers: Optional[bool]
    jumper_pin_groups: List[List[str]]
    properties: List[SchProperty]
    extends: Optional[str]
    symbols: List[SymbolUnit]
    embedded_fonts: Optional[bool]
    embedded_files: List[SchEmbeddedFile]

    @property
    def metadata(self) -> SchematicSymbolMetadata:
        """Gets basic symbol properties"""
        return SchematicSymbolMetadata(
            footprint=self.get_property('Footprint'),
            lcsc_part=self.get_property('LCSC Part'),
            reference=self.get_property('Reference'),
            value=self.get_property('Value'),
            datasheet=self.get_property('Datasheet'),
        )
   
    def get_property(self, key: str, fallback: str | None = None) -> SchProperty | None:
        """Retrieves the property value of the symbol if it exists. The 2nd argument is the fallback if the
        key does not exist. Just like python dict's .get() method"""
        for symbol_property in self.properties:
            if symbol_property.name == key:
                return symbol_property.value
        
        return fallback

    def pinlist(self, unit: int | None = None, variant: int | None = None) -> List[Pin]:
        """Retrieves the array of symbol pins for a given symbol unit and unit variant."""
        pins: List[Pin] = []

        for symbol_unit in self.symbols:
            if (unit is None or symbol_unit._unit == unit or symbol_unit._unit == 0) and (variant is None or symbol_unit._variant == variant or symbol_unit._variant == 0):
                pins.extend(symbol_unit.pins)
        
        return pins

    def get_common_unit(self) -> int:
        """Returns the common unit of the symbol"""
        return next((unit._unit for unit in self.symbols if unit._unit != 0), None)
    
    def has_multiple_units(self) -> bool:
        """Returns True if the symbol has multiple units, False otherwise"""
        return any(unit._unit not in (0, 1) for unit in self.symbols)
    
    def __post_init__(self) -> None:
        """
        Ensures all pins have non-empty names by assigning the pin number as the name
        if the name is an empty string. This is necessary because some symbols from
        external sources (UltraLibrarian, JLC) may have pins with empty names.
        Also handles duplicate pin names by adding _<number> suffix to make them unique.
        All occurrences of duplicate names get suffixes starting from _1.
        """
        all_pins: List[Pin] = []
        for symbol_unit in self.symbols:
            for pin in symbol_unit.pins:
                if pin.name.name in ('', '~'):
                    pin.name.name = str(pin.number.number)
                all_pins.append(pin)


@dataclass(kw_only=True)
class SchReferenceImage:
    at: Vector2D
    scale: float = 1.0
    uuid: Optional[str]
    datas: List[str]


@dataclass(kw_only=True)
class SheetPin:
    name: str = positional()
    shape: str = positional()
    at: Vector2DWithRotation
    effects: Optional[SchEffects]
    uuid: Optional[str]


@dataclass(kw_only=True)
class SheetInstancePath:
    path: str = positional()
    page: str


@dataclass(kw_only=True)
class SheetInstances:
    paths: List[SheetInstancePath]


@dataclass(kw_only=True)
class SchField:
    name: str = positional()
    value: str = positional()
    private: bool = flag_boolean()
    id: Optional[int]
    at: Vector2DWithRotation
    hide: Optional[bool]
    effects: Optional[SchEffects]
    show_name: Optional[bool]
    do_not_autoplace: Optional[bool]


@dataclass(kw_only=True)
class Sheet:
    at: Vector2D
    size: Vector2D
    exclude_from_sim: Optional[bool]
    in_bom: Optional[bool]
    on_board: Optional[bool]
    dnp: Optional[bool]
    fields_autoplaced: Optional[bool]
    stroke: Optional[SchStroke]
    fill: Optional[Fill]
    uuid: Optional[str]
    properties: List[SchField]
    pins: List[SheetPin]
    # todo fixme this is probably wrong and should be fixed
    instances: List[Dict[str, List[SheetInstances]]]


@dataclass
class Color:
    r: int = positional()  # 255
    g: int = positional()
    b: int = positional()
    a: float = positional()  # 0-1


@dataclass(kw_only=True)
class Junction:
    at: Vector2D
    diameter: Optional[float]
    color: Optional[Color]
    uuid: Optional[str]


@dataclass(kw_only=True)
class NoConnectMark:
    at: Vector2D
    uuid: Optional[str]


@dataclass(kw_only=True)
class BusEntry:
    at: Vector2D
    size: Optional[Vector2D]
    stroke: Optional[SchStroke]
    uuid: Optional[str]


@dataclass(kw_only=True)
class Bus:
    size: Optional[Vector2D]
    pts: Optional[SchShapeLineChain]
    stroke: Optional[SchStroke]
    uuid: Optional[str]


@dataclass(kw_only=True)
class SchPolyline:
    pts: Optional[SchShapeLineChain]
    stroke: Optional[SchStroke]
    fill: Optional[Fill]
    uuid: Optional[str]


@dataclass(kw_only=True)
class SchArc:
    start: Vector2D
    mid: Vector2D
    end: Vector2D
    stroke: Optional[SchStroke]
    fill: Optional[Fill]
    uuid: Optional[str]


@dataclass(kw_only=True)
class SchCircle:
    center: Vector2D
    radius: float
    stroke: Optional[SchStroke]
    fill: Optional[Fill]
    uuid: Optional[str]


@dataclass(kw_only=True)
class SchRectangle:
    start: Vector2D
    end: Vector2D
    radius: Optional[float]
    stroke: Optional[SchStroke]
    fill: Optional[Fill]
    uuid: Optional[str]


@dataclass(kw_only=True)
class SchBezier:
    pts: Optional[SchShapeLineChain]
    stroke: Optional[SchStroke]
    fill: Optional[Fill]
    uuid: Optional[str]


@dataclass(kw_only=True)
class SchRuleArea:
    polyline: Optional[SchPolyline]
    exclude_from_sim: Optional[bool]
    in_bom: Optional[bool]
    on_board: Optional[bool]
    dnp: Optional[bool]


@dataclass(kw_only=True)
class BusAlias:
    name: str = positional()
    memberss: List[str]


@dataclass(kw_only=True)
class SchGroup:
    name: Optional[str] = positional()
    uuid: Optional[str]
    lib_id: Optional[str]
    members: List[str]


@dataclass(kw_only=True)
class TableCell:
    text: str = positional()
    at: Vector2DWithRotation
    size: Optional[Vector2D]
    stroke: Optional[SchStroke]
    fill: Optional[Fill]
    margins: Optional[Margins]
    effects: Optional[SchEffects]
    span: Optional[Tuple[int, int]]
    uuid: Optional[str]


@dataclass(kw_only=True)
class SchTableBorder:
    external: bool
    header: bool
    stroke: Optional[SchStroke]


@dataclass(kw_only=True)
class SchTableSeparators:
    rows: bool
    cols: bool
    stroke: Optional[SchStroke]


@dataclass(kw_only=True)
class SchTable:
    column_count: int
    column_widths: List[float]
    row_heights: List[float]
    cells: List[TableCell]
    border: Optional[SchTableBorder]
    separators: Optional[SchTableSeparators]
    uuid: Optional[str]


@dataclass(kw_only=True)
class SchText:
    text: str = positional()
    shape: Optional[str]
    exclude_from_sim: Optional[bool]
    at: Vector2DWithRotation
    length: Optional[float]
    fields_autoplaced: Optional[bool]
    effects: Optional[SchEffects]
    iref: Optional[Vector2D]
    uuid: Optional[str]
    properties: List[SchField]


@dataclass(kw_only=True)
class SchSymbolInstancePath:
    path: str = positional()
    reference: str
    unit: int


@dataclass(kw_only=True)
class SchSymbolInstance:
    name: str = positional()
    path: SchSymbolInstancePath
    # todo implement this
    # variants: Optional[Dict[str, Dict[str, Union[bool, str]]]]


@dataclass
class InstanceList:
    projects: List[SchSymbolInstance]


@dataclass(kw_only=True)
class SchSymbol:
    lib_id: Optional[str]
    lib_name: Optional[str]
    at: Vector2DWithRotation
    mirror: Optional[str]
    unit: int
    body_style: Optional[int]
    exclude_from_sim: Optional[bool]
    in_bom: Optional[bool]
    on_board: Optional[bool]
    dnp: Optional[bool]
    fields_autoplaced: Optional[bool]
    uuid: Optional[str]
    default_instance: Optional[Dict[str, Union[str, int]]]
    properties: List[SchProperty]
    pins: List[Pin]
    instances: Optional[InstanceList]

    def __hash__(self):
        """Make the symbol instance hashable based on its UUID"""
        return hash(self.uuid) if self.uuid else hash(id(self))
    
    def __eq__(self, other):
        """Compare symbol instances based on their UUID"""
        if not isinstance(other, SchSymbol):
            return False
        return self.uuid == other.uuid
    
    def get_property(self, key: str) -> SchProperty | None:
        """Retrieves the property value of the symbol if it exists"""
        for symbol_property in self.properties:
            if symbol_property.name == key:
                return symbol_property.value
        
        return None


@dataclass
class Wire:
    pts: SchShapeLineChain
    stroke: SchStroke
    uuid: str


@dataclass
class LibSymbols:
    symbols: List[LibSymbol]


@dataclass(kw_only=True)
class SymbolLibrary(SexprMixin):
    """ For parsing .kicad_sym files """
    version: int
    generator: str
    generator_version: Optional[str]
    symbols: List[LibSymbol]

    def get_symbol(self, chip_id: str, property_key: str = "LCSC Part") -> LibSymbol:
        """
        Fetches the schematic symbol with a given ID (right now using LCSC Part property) from the symbol library
        Parameters:
            chip_id (str): ID of the requested chip
            property_key (str): KiCad property under which to look for the ID match

        Returns:
            LibSymbol: KiCad schematic symbol object

        Raises:
            MissingSchematicSymbolException
        """
        for symbol in self.symbols:
            symbol_id_property = symbol.get_property(property_key)
            if symbol_id_property is not None and symbol_id_property == chip_id:
                return symbol
        else:
            raise MissingSchematicSymbolException(chip_id)


@dataclass(kw_only=True)
class Schematic(SexprMixin):
    """ For parsing .kicad_sch files """
    version: int
    generator: Optional[str]
    generator_version: Optional[str]
    uuid: Optional[str]
    paper: Optional[SchPageInfo]
    page: Optional[Tuple[str, str]]
    title_block: Optional[SchTitleBlock]
    lib_symbols: Optional[LibSymbols]
    bus_aliass: List[BusAlias]
    arcs: List[SchArc]
    circles: List[SchCircle]
    rectangles: List[SchRectangle]
    texts: List[SchText]
    text_boxes: List[SchTextBox]
    junctions: List[Junction]
    bus_entries: List[BusEntry]
    sheets: List[Sheet]
    no_connects: List[NoConnectMark]
    wires: List[Wire]
    images: List[SchReferenceImage]
    polylines: List[SchPolyline]
    buss: List[Bus]
    beziers: List[SchBezier]
    rule_areas: List[SchRuleArea]
    labels: List[SchText]
    global_labels: List[SchText]
    hierarchical_labels: List[SchText]
    directive_labels: List[SchText]
    netclass_flags: List[SchText]
    tables: List[SchTable]
    symbol_instances: List[Dict[str, List[SchSymbolInstance]]]
    symbols: List[SchSymbol]
    sheet_instances: Optional[SheetInstances]
    embedded_fonts: Optional[bool]
    embedded_files: List[SchEmbeddedFile]
    groups: List[SchGroup]

    _preserve_interleaved_order = ['wires', 'polylines', 'buss']

    @property
    def connection_lines(self) -> list[Bus | Wire | SchPolyline]:
        """Returns a list of items that are used to draw connections between pins."""
        return self.wires + self.polylines + self.buss

    def _all_pin_locs(self) -> List[PinLoc]:
        """
        Return every pin in the design with absolute coordinates.
        Handles both flat and unit-based symbol libraries.
        """
        pins: list[PinLoc] = []

        # Build a mapping from libId to libSymbol for fast lookup
        lib_id_map = {lib.name: lib for lib in self.lib_symbols.symbols}

        # For each schematic symbol instance
        for symbol_instance in self.symbols:
            # Find the parent libSymbol by instance libId
            parent_lib_symbol = lib_id_map.get(symbol_instance.lib_id)
          
            # Offset the pin location by the instance position
            chip_position = Vector2DWithRotation(
                x=Decimal(str(symbol_instance.at.x)),
                y=Decimal(str(symbol_instance.at.y)),
                rot=Decimal(str(symbol_instance.at.rot))
            )
            
            # If the parent symbol does not have multiple units and the symbol instance unitId is 0, change it to 1 for pinlist
            pinlist_unit = symbol_instance.unit
            if not parent_lib_symbol.has_multiple_units() and pinlist_unit == 0:
                pinlist_unit = 1
                
            for pin in parent_lib_symbol.pinlist(unit=pinlist_unit, variant=symbol_instance.body_style):
                # Power symbols used to required having their pins marked as hidden (even though they show)
                # in older versions of kicad: https://klc.kicad.org/symbol/s7/s7.1/
                if pin.hide and not parent_lib_symbol.power:
                    continue  # don't plot hidden pins
                # The order which kicad applies reflections and rotations:
                #     for( int i = 0; i < o.n_rots; i++ )
                #         item.Rotate( VECTOR2I( 0, 0 ), true );
                #     if( o.mirror_x )
                #         item.MirrorVertically( 0 );
                #     if( o.mirror_y )
                #         item.MirrorHorizontally( 0 );
                # https://github.com/KiCad/kicad-source-mirror/blob/8c017c7503d530d0fb7900360bed033ac80eb12b/eeschema/symb_transforms_utils.cpp#L56
                pin_position = Vector2DWithRotation(
                    x=Decimal(str(pin.at.x)),
                    y=-Decimal(str(pin.at.y)),  # For some reason (idk why), pin's y coordinates need to be negated
                    rot=Decimal(str(pin.at.rot))
                )
                angle = symbol_instance.at.rot
                if angle is not None:
                    pin_position.rotate_about_origin(-angle)
                if symbol_instance.mirror is not None:
                    if symbol_instance.mirror == 'x':  # mirror about x axis
                        pin_position.y = -pin_position.y
                    elif symbol_instance.mirror == 'y':  # mirror about y axis
                        pin_position.x = -pin_position.x
                    else:
                        Exception(f"A symbol's mirror value is not 'x' or 'y', it is {symbol_instance.mirror}")
                absolute_position = pin_position + chip_position
                pins.append(PinLoc(symbol_inst=symbol_instance, pin=pin, pos=absolute_position))

        return pins

    def find_symbol_instance_parent(self, symbol_instance: SchSymbol) -> LibSymbol:
        """
        Finds the parent symbol of a symbol instance.
        """
        lib_symbol = next((lib for lib in self.lib_symbols.symbols if lib.name == symbol_instance.lib_id), None)
        if lib_symbol is None:
            raise Exception(f"Lib symbol not found for {symbol_instance.lib_id}. This should never happen.")
        return lib_symbol

    def to_autopcb_subcircuit(self, subcircuit_name: str) -> str:
        """
        Converts the schematic to an AutoPCB subcircuit.
        """
        lines: list[str] = []
        
        lines.append("from autopcb.core import *\n")
        lines.append(f"class {subcircuit_name}(Subcircuit):")
        lines.append("  def build(pcb):")

        # Generate unique variable names for all symbols
        symbol_to_varname = generate_unique_variable_names(self.symbols)

        for i, inst in enumerate(self.symbols):
            varname = symbol_to_varname[inst]
                
            x = kicad_to_autopcb_units(inst.at.x)
            y = kicad_to_autopcb_units(inst.at.y)
            rotation = inst.at.rot
            reflect = inst.mirror
            position = f"x={x}, y={y}" \
                + (f", rotate={rotation}" if rotation is not None else "") \
                + (f", reflect='{reflect}'" if reflect is not None else "")

            symbol_parent = self.find_symbol_instance_parent(inst)
            if symbol_parent.power:
                if any(k in inst.lib_id for k in ("GND", "Earth")):
                    lines.append(
                        f"    {varname} = pcb.GND({position})"
                    )
                else:
                    lines.append(
                        f"    {varname} = pcb.Power('{inst.get_property('Value')}', {position})"
                    )
            else:
                # Units with ID equal to 0 are common to all other units, and if there is only unit with ID 1 otherwise,
                # it means the symbol does not have true real subunits
                if symbol_parent.has_multiple_units():
                    unit_kwarg = f", unit={inst.unit}"
                    varname_unit = f"{varname}{generate_alphabetical_suffix(inst.unit)}"
                else:
                    unit_kwarg = ""
                    varname_unit = varname
                    
                variant_kwarg = f", variant={inst.body_style}" if inst.body_style is not None else ""
                
                lines.append(
                    f"    {varname_unit} = pcb.Part('{inst.get_property('Value')}', {position}{unit_kwarg}{variant_kwarg})"
                )

        lines.append("")  

        for i, txt in enumerate(self.texts):
            lines.append(
                f"    TXT{i} = pcb.Text('{txt.text}', "
                f"x={kicad_to_autopcb_units(txt.at.x)}, y={kicad_to_autopcb_units(txt.at.y)}, "
                f"size={round(10 * txt.effects.font.size.x)})"
            )

        for i, nc in enumerate(self.no_connects):
            lines.append(
                f"    NC{i} = pcb.NoConnect("
                f"x={kicad_to_autopcb_units(nc.at.x)}, y={kicad_to_autopcb_units(nc.at.y)})"
            )      
            
        for i, nl in enumerate(self.labels + self.global_labels):
            lines.append(
                f"    NL{i} = pcb.NetLabel('{nl.text}', "
                f"x={kicad_to_autopcb_units(nl.at.x)}, y={kicad_to_autopcb_units(nl.at.y)})"
            )

        extractor = SchematicConnectionExtractor(self, timeout=20, symbol_to_varname=symbol_to_varname)
        connection_str = extractor.generate_connection_strings()
        lines.append(connection_str)

        return "\n".join(lines)


"""
This file contains a custom implementation of Kicad schematic parsers that build on top of Kiutils
parsing library. We need these inherited classes to provide additional methods to simplify property access and rendering,
and provide property typing for graphic elements.
"""


class SchematicConnectionExtractor:
    """
    Extracts and computes optimal connection paths between pins in a KiCad schematic.

    This class provides an API to analyze a schematic and generate connection
    instructions (e.g., for PCB layout) by finding optimal paths between pins,
    considering already rendered edges and existing connections.

    Attributes:
        schematic (Schematic): The schematic to analyze.
        timeout (float): Maximum time (in seconds) to spend on the graph search.
        plot_with_matplotlib_for_debug (bool): Uncomment this if you want debug plotting for the algorithm that covert
            kicad wires (effectively a large collection of line segments) to AutoPCB's traces (pin to pin `pcb.connect()`)
    """

    def __init__(self, schematic: "Schematic", symbol_to_varname: Dict[SchSymbolInstance, str], timeout: float = 5, plot_with_matplotlib_for_debug=False):
        self.schematic = schematic
        self.timeout = timeout
        self.plot_with_matplotlib_for_debug = plot_with_matplotlib_for_debug
        self.adjacent_nodes: Dict[Point, List[Edge]] = {}
        self.pins_at_position: Dict[Point, List[str]] = {}
        self.edges_already_rendered: Set[Tuple[Point, Point]] = set()
        self.nodes_already_connected: Set[Point] = set()
        self.paths_completed: List[List[Point]] = []
        self.symbol_to_varname: Dict[SchSymbolInstance, str] = symbol_to_varname
        self._build_graph()
        self._build_pins_at_position()

    def _build_graph(self):
        adj_nodes: Dict[Point, List[Edge]] = defaultdict(list)
        for line_segment in self.schematic.connection_lines:
            if line_segment.pts is None or len(line_segment.pts.xys) != 2:
                raise NotImplementedError("A line in a schematic must have exactly 2 points")
            point_a = (line_segment.pts.xys[0].x, line_segment.pts.xys[0].y)
            point_b = (line_segment.pts.xys[1].x, line_segment.pts.xys[1].y)
            distance = math.sqrt((point_a[0] - point_b[0]) ** 2 + (point_a[1] - point_b[1]) ** 2)
            adj_nodes[point_a].append(Edge(other_node=point_b, distance=distance))
            adj_nodes[point_b].append(Edge(other_node=point_a, distance=distance))
        # we no longer want to silently create an empty list for adjacent nodes to append
        # if there's a key error, it's a real error that should be raised
        self.adjacent_nodes = dict(adj_nodes)

    def _build_pins_at_position(self):
        # key: a coordinate; value: list of pins at that coordinate
        pins: Dict[Point, List[str]] = defaultdict(list)
        for point in self.schematic._all_pin_locs():
            # Get the correct variable name for this symbol instance
            if point.symbol_inst in self.symbol_to_varname:
                varname = self.symbol_to_varname[point.symbol_inst]
            else:
                # Fallback to original reference if mapping not available
                ref = point.symbol_inst.get_property("Reference")
                varname = replace_illegal_python_chars(ref)
            
            # Check if this symbol has multiple units and add unit suffix if needed
            symbol_parent = self.schematic.find_symbol_instance_parent(point.symbol_inst)
            if symbol_parent and symbol_parent.has_multiple_units():
                varname = f"{varname}{generate_alphabetical_suffix(point.symbol_inst.unit)}"
            elif symbol_parent and not symbol_parent.has_multiple_units():
                # If the parent symbol does not have multiple units and the symbol instance unitId is 0, change it to 1
                unit_id = point.symbol_inst.unit
                if unit_id == 0:
                    unit_id = 1
            
            if symbol_parent and symbol_parent.power is not None:
                pin_name = '1'
            else:
                pin_name = point.pin.name.name if point.pin.name.name != '' else (point.pin.number.number if point.pin.number.number != '' else '1')
            ref_and_pin = f"{varname}['{pin_name}']"
            # Using float() to convert Decimal back to floats
            #  which is ok *as long as* we don't need to do any arithmatic operations anymore
            #  otherwise we need to keep using Decimal
            pins[(float(point.pos.x), float(point.pos.y))].append(ref_and_pin)
        for idx, point in enumerate(self.schematic.no_connects):
            pins[(point.at.x, point.at.y)].append(f"NC{idx}['1']")
        for idx, point in enumerate(self.schematic.labels + self.schematic.global_labels):
            pins[(point.at.x, point.at.y)].append(f"NL{idx}['1']")
        # we no longer want to silently create an empty list for adjacent nodes to append
        # if there's a key error, it's a real error that should be raised
        self.pins_at_position = dict(pins)  # key: a coordinate; value: list of pins at that coordinate

    def _path_length(self, path: List[Point]) -> float:
        """Calculate the path length, weighting segments that already are rendered as distance = 0"""
        length = 0
        for point_a, point_b in zip(path[:-1], path[1:]):
            if (point_a, point_b) in self.edges_already_rendered or (point_b, point_a) in self.edges_already_rendered:
                continue
            length += math.sqrt((point_b[0] - point_a[0]) ** 2 + (point_b[1] - point_a[1]) ** 2)
        return length

    def _optimal_path_to_add(self) -> Optional[List[Point]]:
        """Return the optimal path to create a connection. "Optimal" means:
        - if the net doesn't have a longest connection yet, return that
        - if the net already has a longest connection, then return small paths from a pin to the connection
        This makes it easy to understand visually: there appears to be a long bus wire, with all the other
        pins in the net connected having small connections up to the bus"""
        visited = set()
        max_path: List[Point] = []
        stub_path: Optional[List[Point]] = None  # a connection from a pin to another connection (typically short)

        def dfs(node, path):
            nonlocal max_path, stub_path
            visited.add(node)
            path.append(node)

            extended = False
            for neighbor_edge in self.adjacent_nodes[node]:
                neighbor = neighbor_edge.other_node
                # To prevent any cycles
                if neighbor not in path:  
                    dfs(neighbor, path)
                    extended = True

            path_ends_on_pin = path[-1] in self.pins_at_position
            is_leaf_node = not extended
            is_longer_than_longest_path = self._path_length(path) > self._path_length(max_path)
            ends_on_a_node_that_already_has_a_connection = (
                # If the path ends on a vertex that already has a connection
                # check to make sure it's not already connected
                path[-1] in self.nodes_already_connected
                and len(path) > 1 
                and (path[0], path[1]) not in self.edges_already_rendered
                and (path[1], path[0]) not in self.edges_already_rendered
            )
            if ends_on_a_node_that_already_has_a_connection:
                stub_path = path[:]
            elif path_ends_on_pin and is_leaf_node and is_longer_than_longest_path:
                # Shallow copy "path", since it will be mutated
                max_path = path[:]  

            path.pop()
            visited.remove(node)

        for start in self.pins_at_position:
            # If there's no connection starting from this pin, skip it
            if start not in self.adjacent_nodes:
                continue
            dfs(start, [])

        if stub_path is not None:
            return stub_path
        elif max_path:
            return max_path
        else:
            return None

    def _get_pin_from_connection_that_has_point(self, point: Point) -> str:
        for other_path in self.paths_completed:
            if point in other_path:
                # We can take the pins at either end of the other connection as potential start pins
                available_pins = self.pins_at_position.get(other_path[0], []) + self.pins_at_position.get(other_path[-1], [])
                if not available_pins:
                    raise Exception('Start pin not found')
                return available_pins[0]
        raise Exception('No completed path contains the given point')

    def extract_connections(self) -> List[Tuple[str, str, List[Point]]]:
        """
        Extracts the optimal set of connections from the schematic.

        Returns:
            List of tuples: (start_pin, end_pin, vertices)
        """
        self.edges_already_rendered.clear()
        self.nodes_already_connected.clear()
        self.paths_completed.clear()
        start_time = time.time()
        connections: List[Tuple[str, str, List[Point]]] = []

        if self.plot_with_matplotlib_for_debug:
            import matplotlib.pyplot as plt
            point_size = 2
            plt.gcf().set_size_inches(18.5, 10.5)
            for line_segment in self.schematic.graphicalItems:
                plt.plot([point.X for point in line_segment.points],
                         [point.Y for point in line_segment.points],
                         '.-',
                         markersize=1,
                         linewidth=0.7)
            for point in self.schematic._all_pin_locs():
                plt.plot(point.pos.x, point.pos.y, 'x', markersize=point_size)
            for point in self.schematic.no_connects:
                plt.plot(point.at.x, point.at.y, 'x', markersize=point_size)
            for point in self.schematic.labels:
                plt.plot(point.at.x, point.at.y, 'x', markersize=point_size)
            for point in self.schematic.global_labels:
                plt.plot(point.at.x, point.at.y, 'x', markersize=point_size)

        while time.time() < start_time + self.timeout:
            path_to_add = self._optimal_path_to_add()
            if path_to_add is None:
                # We're done: we added all the paths we can add
                break
            self.paths_completed.append(path_to_add)
            for point_a, point_b in zip(path_to_add[:-1], path_to_add[1:]):
                self.edges_already_rendered.add((point_a, point_b))
            for point in path_to_add:
                self.nodes_already_connected.add(point)

            vertices = path_to_add[:]
            if path_to_add[0] in self.pins_at_position:
                # It shouldn't matter if there are other pins at the same position, since we have code that autoconnects pins at the same position
                start_pin = self.pins_at_position[path_to_add[0]][0]  
                # If the first vertex is the pin, it is implicit and not needed as an arg
                vertices = vertices[1:]  
            else:
                # The start is on another connection, so we need to follow the other connection to get the pin
                start_pin = self._get_pin_from_connection_that_has_point(path_to_add[0])
            # See comments above for explanation
            if path_to_add[-1] in self.pins_at_position:
                end_pin = self.pins_at_position[path_to_add[-1]][0]
                vertices = vertices[:-1]
            else:
                end_pin = self._get_pin_from_connection_that_has_point(path_to_add[-1])

            connections.append((start_pin, end_pin, vertices))
            if self.plot_with_matplotlib_for_debug:
                plt.plot([point[0] for point in path_to_add], [point[1] for point in path_to_add], 'o-')
        else:
            raise TimeoutError('Timed out while extracting connections')

        if self.plot_with_matplotlib_for_debug:
            plt.gca().invert_yaxis()
            plt.show()

        return connections

    def generate_connection_strings(self) -> str:
        """
        Generates the connection strings for the extracted connections.

        Returns:
            str: The formatted connection instructions.
        """
        connections = self.extract_connections()
        connection_lines = []
        for start_pin, end_pin, vertices in connections:
            vertices_string = ''
            if vertices:
                vertices_arg_value = ', '.join([f'({kicad_to_autopcb_units(vertex[0])},{kicad_to_autopcb_units(vertex[1])})' for vertex in vertices])
                vertices_string = f', vertices=[{vertices_arg_value}]'
            connection_lines.append(f"    pcb.connect({fix_connection_args_to_be_legal(start_pin)}, {fix_connection_args_to_be_legal(end_pin)}{vertices_string})")
        return '\n'.join(connection_lines)


def fix_connection_args_to_be_legal(pin_with_index: str):
    """Replaces a string that would be an arg for pcb.connect() to
    replace illegal python chars *only for the variable name* and not the
    pin names (since those are strings, so we can keep stuff like $ in them)"""
    pin_split = pin_with_index.split('[')
    pin_var, pin_rest_of_string = pin_split[0], '[' + '['.join(pin_split[1:])
    pin = replace_illegal_python_chars(pin_var) + pin_rest_of_string
    return pin


def replace_illegal_python_chars(arg: str):
    return arg.replace("#", "hash").replace("$", "dol").replace("+", "plus").replace("?", "qmark").replace("&", "amp").replace('*', 'star').replace('~', 'til')


def generate_unique_variable_names(schematic_symbols: List[SchSymbol]) -> Dict[SchSymbol, str]:
    """
    Generates unique variable names for schematic symbols, handling duplicate references.
    
    Args:
        schematic_symbols: List of schematic symbol instances
        
    Returns:
        Dictionary mapping symbol instance to unique variable name
    """
    reference_counts: Dict[str, int] = {}
    symbol_to_varname: Dict[SchSymbol, str] = {}
    
    # First pass: count occurrences of each reference
    for symbol in schematic_symbols:
        reference = symbol.get_property("Reference")
        
        if reference is None:
            raise Exception(f"Reference property not found for symbol {symbol.name}")
        
        reference_counts[reference] = reference_counts.get(reference, 0) + 1
    
    # Second pass: assign unique variable names
    reference_used_count: Dict[str, int] = {}
    
    for symbol in schematic_symbols:
        reference = symbol.get_property("Reference")
        
        if reference is None:
            raise Exception(f"Reference property not found for symbol {symbol.name}")
        
        # Create base variable name
        base_varname = replace_illegal_python_chars(reference)
        
        # If this reference appears multiple times, add a numeric suffix
        if reference_counts[reference] > 1:
            reference_used_count[reference] = reference_used_count.get(reference, 0) + 1
            unique_varname = f"{base_varname}{reference_used_count[reference]}"
        else:
            unique_varname = base_varname
        
        symbol_to_varname[symbol] = unique_varname
    
    return symbol_to_varname