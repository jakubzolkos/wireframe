from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
import math
import re
import sys
import time
from typing import Any, List, Optional, Set, Union, Dict, Tuple

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


"""
This file contains a custom implementation of Kicad schematic parsers that build on top of Kiutils
parsing library. We need these inherited classes to provide additional methods to simplify property access and rendering,
and provide property typing for graphic elements.
"""

