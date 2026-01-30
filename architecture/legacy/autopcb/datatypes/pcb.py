from dataclasses import dataclass, field
from itertools import chain
import itertools
from typing import Iterable, List, Optional, Set, Union, Dict, Tuple
from uuid import uuid4

from autopcb.datatypes.common import Margins, BoundingBox, Vector2D, Vector2DWithRotation
from autopcb.datatypes.fields import flag_boolean, positional
from autopcb.datatypes.utils import get_arc_bounding_box, normalize_angle
from autopcb.datatypes.mixins import DataclassSerializerMixin, SexprMixin


@dataclass(kw_only=True)
class Vector3D:
    x: float = positional()                                                                     
    y: float = positional()
    z: float = positional()


@dataclass(kw_only=True)
class Arc:
    start: Vector2D
    mid: Optional[Vector2D]
    end: Vector2D


@dataclass(kw_only=True)
class ShapeLineChain:
    xys: List[Vector2D]
    arcs: List[Arc]
    _preserve_interleaved_order: List[str] = field(default_factory=lambda: ['xys', 'arcs'])


@dataclass(kw_only=True)
class Layer:
    index: int = positional()
    name: str = positional()
    type: str = positional()
    # the kicad source code says "// @todo Figure out why we are looking for a hide token in the layer definition."
    # lol
    #visible: bool = True
    user_name: Optional[str] = positional()

    _index_from_0 = True


@dataclass(kw_only=True)
class PageInfo:
    type: str = positional()
    width: Optional[float]
    height: Optional[float]
    portrait: bool = flag_boolean()


@dataclass(kw_only=True)
class TitleBlockComment:
    index: int
    text: str

@dataclass(kw_only=True)
class TitleBlock:
    title: Optional[str]
    date: Optional[str]
    rev: Optional[str]
    company: Optional[str]
    comments: List[str]


@dataclass(kw_only=True)
class BoardStackupItemThickness:
    thickness: float = positional()
    locked: bool = flag_boolean()


@dataclass(kw_only=True)
class BoardStackupItem:
    layer: Optional[str] = positional()
    type: str
    color: Optional[str]
    thickness: Optional[BoardStackupItemThickness]
    material: Optional[str]
    epsilon_r: Optional[float]
    loss_tangent: Optional[float]
    sublayers: List['BoardStackupItem']


@dataclass(kw_only=True)
class BoardStackup:
    # We need the _ because the parser will try to do 2 things:
    # since it's a list, the last char will be removed when matching the sexpression 0th element items
    # because typically the list is defined like this `(board_stackup (layer stuff stuff) (layer stuff stuff))`
    # the attribute layers is treated special, but we don't want this treated special, so don't use 'layers'
    layer_: List[BoardStackupItem]
    copper_finish: Optional[str]
    dielectric_constraints: bool
    edge_connector: Optional[str]
    edge_plating: Optional[bool]


@dataclass(kw_only=True)
class General:
    thickness: Optional[float]
    legacy_teardrops: Optional[bool]


@dataclass(kw_only=True)
class DimensionDefaults:
    size: Optional[Vector2D]
    thickness: Optional[float]
    italic: bool
    keep_upright: bool


@dataclass(kw_only=True)
class Defaults:
    edge_clearance: Optional[float]
    copper_line_width: Optional[float]
    copper_text_dims: Optional[DimensionDefaults]
    courtyard_line_width: Optional[float]
    edge_cuts_line_width: Optional[float]
    silk_line_width: Optional[float]
    silk_text_dims: Optional[DimensionDefaults]
    fab_layers_line_width: Optional[float]
    fab_layers_text_dims: Optional[DimensionDefaults]
    other_layers_line_width: Optional[float]
    other_layers_text_dims: Optional[DimensionDefaults]
    dimension_units: Optional[int]
    dimension_precision: Optional[int]


@dataclass(kw_only=True)
class TeardropParameters:
    # todo fixme I think most of these are wrong
    enabled: bool
    allow_two_segments: bool
    prefer_zone_connections: bool
    best_length_ratio: Optional[float]
    max_length: Optional[float]
    best_width_ratio: Optional[float]
    max_width: Optional[float]
    curved_edges: bool
    filter_ratio: Optional[float]


@dataclass(kw_only=True)
class ZoneLayerProperties:
    layer: int
    hatching_offset: Optional[Vector2D]


@dataclass(kw_only=True)
class ZoneDefaults:
    properties: List[ZoneLayerProperties]


@dataclass(kw_only=True)
class PcbPlotParams:
    # selection masks (KiCad writes hex like 0x..., older files may write integers).
    # Keep as str to preserve exact representation round-trip.
    layerselection: Optional[str]
    plot_on_all_layers_selection: Optional[str]
    # Gerber
    disableapertmacros: Optional[bool]
    usegerberextensions: Optional[bool]
    usegerberattributes: Optional[bool]
    usegerberadvancedattributes: Optional[bool]
    creategerberjobfile: Optional[bool]
    gerberprecision: Optional[int]
    # Dashed line ratios
    dashed_line_dash_ratio: Optional[float]
    dashed_line_gap_ratio: Optional[float]
    # SVG
    svgprecision: Optional[int]
    svguseinch: Optional[bool]  # present in files; ignored by KiCad now
    plotframeref: Optional[bool]
    mode: Optional[int]
    useauxorigin: Optional[bool]
    # Deprecated HPGL tokens – still appear in some files; treat as raw ints
    hpglpennumber: Optional[int]
    hpglpenspeed: Optional[int]
    hpglpenoverlay: Optional[int]
    hpglpendiameter: Optional[float]
    # PostScript
    pdf_front_fp_property_popups: Optional[bool]
    pdf_back_fp_property_popups: Optional[bool]
    pdf_metadata: Optional[bool]
    pdf_single_document: Optional[bool]
    # DXF
    dxfpolygonmode: Optional[bool]
    dxfimperialunits: Optional[bool]
    dxfusepcbnewfont: Optional[bool]
    # PostScript
    psnegative: Optional[bool]
    psa4output: Optional[bool]
    pscolor: Optional[str]       # token exists; KiCad ignores value
    # Misc flags
    excludeedgelayer: Optional[bool]
    viasonmask: Optional[bool]
    plot_black_and_white: Optional[bool]
    plotinvisibletext: Optional[bool]  # legacy; still parse for compatibility
    sketchpadsonfab: Optional[bool]
    plotpadnumbers: Optional[bool]
    hidednponfab: Optional[bool]
    sketchdnponfab: Optional[bool]
    crossoutdnponfab: Optional[bool]
    subtractmaskfromsilk: Optional[bool]
    outputformat: Optional[int]
    mirror: Optional[bool]
    # Enumerated/int-like settings (store raw ints; no range validation here)
    drillshape: Optional[int]
    scaleselection: Optional[int]
    # Paths
    outputdirectory: Optional[str]


@dataclass(kw_only=True)
class Setup:
    stackup: Optional[BoardStackup]
    last_trace_width: Optional[float]
    user_trace_width: List[float]
    trace_clearance: Optional[float]
    zone_clearance: Optional[float]
    zone_45_only: Optional[bool]
    clearance_min: Optional[float]
    trace_min: Optional[float]
    via_size: Optional[float]
    via_drill: Optional[float]
    via_min_annulus: Optional[float]
    via_min_size: Optional[float]
    through_hole_min: Optional[float]
    uvia_size: Optional[float]
    uvia_drill: Optional[float]
    uvias_allowed: Optional[bool]
    blind_buried_vias_allowed: Optional[bool]
    uvia_min_size: Optional[float]
    uvia_min_drill: Optional[float]
    user_diff_pair: List[Tuple[float, float, float]]
    defaults: Optional[Defaults]
    pad_size: Optional[Vector2D]
    pad_drill: Optional[float]
    pad_to_mask_clearance: Optional[float]
    solder_mask_min_width: Optional[float]
    pad_to_paste_clearance: Optional[float]
    pad_to_paste_clearance_ratio: Optional[float]
    allow_soldermask_bridges_in_footprints: Optional[bool]
    tentings: List[str]
    covering: List[str]
    plugging: List[str]
    capping: Optional[bool]
    filling: Optional[bool]
    aux_axis_origin: Optional[Vector2D]
    grid_origin: Optional[Vector2D]
    visible_elements: Optional[int]
    max_error: Optional[float]
    filled_areas_thickness: Optional[bool]
    pcbplotparams: Optional[PcbPlotParams]
    zone_defaults: Optional[ZoneDefaults]


@dataclass(kw_only=True)
class Font:
    face: Optional[str]
    size: Optional[Vector2D]
    line_spacing: Optional[float]
    thickness: Optional[float]
    bold: Optional[bool]
    italic: Optional[bool]


@dataclass(kw_only=True)
class Effects:
    font: Optional[Font]
    justifies: List[str]
    hide: Optional[bool]


@dataclass(kw_only=True)
class Property:
    # the mounting hole file (in a library, not placed on a board) did not have some of these attributes
    name: str = positional()
    value: str = positional()
    at: Optional[Vector2DWithRotation]
    unlocked: Optional[bool]
    layer: Optional[str]
    hide: Optional[bool]
    uuid: Optional[str]
    effects: Optional[Effects]


@dataclass(kw_only=True)
class Net:
    number: int = positional()
    name: str = positional()


@dataclass(kw_only=True)
class NetClass:
    name: str
    description: str
    clearance: Optional[float]
    trace_width: Optional[float]
    via_dia: Optional[float]
    via_drill: Optional[float]
    uvia_dia: Optional[float]
    uvia_drill: Optional[float]
    diff_pair_width: Optional[float]
    diff_pair_gap: Optional[float]
    add_nets: List[str]


@dataclass(kw_only=True)
class ListOfPoints:
    pts: List[ShapeLineChain]


@dataclass(kw_only=True)
class RenderCache:
    text: str = positional()
    angle: float = positional()
    polygons: List[ListOfPoints]


@dataclass(kw_only=True)
class Color:
    r: int = positional()  # 255
    g: int = positional()
    b: int = positional()
    a: float = positional()  # 0-1


@dataclass(kw_only=True)
class Stroke:
    width: float
    type: str = "solid"  # solid, dash, dash_dot, dash_dot_dot, dot, default
    color: Optional[Color]


@dataclass(kw_only=True)
class ReferenceImage:
    at: Vector2DWithRotation
    layer: Optional[str]
    scale: float = 1.0
    data: Optional[str]
    locked: bool = False
    uuid: Optional[str]


@dataclass(kw_only=True)
class LayoutText:
    type: Optional[str]
    text: str
    locked: bool
    # todo fixme the `at` attribute is wrong
    at: Optional[Vector2DWithRotation]
    layer: Optional[str]
    knockout: bool
    hide: bool
    unlocked: bool
    effects: Optional[Effects]
    render_cache: Optional[RenderCache]
    tstamp: Optional[str]
    uuid: Optional[str]


@dataclass
class TextBox:
    locked: bool
    text: str
    start: Optional[Vector2D]
    end: Optional[Vector2D]
    pts: Optional[ShapeLineChain]
    angle: Optional[float]
    stroke: Optional[Stroke]
    border: bool
    margins: Optional[Tuple[float, float, float, float]]
    layer: Optional[str]
    knockout: bool
    span: Optional[Tuple[int, int]]
    effects: Optional[Effects]
    render_cache: Optional[RenderCache]
    uuid: Optional[str]
    tstamp: Optional[str]


@dataclass
class TableBorder:
    external: bool
    header: bool
    stroke: Optional[Stroke]


@dataclass
class TableSeparators:
    rows: bool
    cols: bool
    stroke: Optional[Stroke]


@dataclass
class Table:
    column_count: int
    locked: bool
    layer: Optional[str]
    column_widths: List[float]
    row_heights: List[float]
    cells: List[TextBox]
    border: Optional[TableBorder]
    separators: Optional[TableSeparators]


@dataclass
class DimensionFormat:
    prefix: Optional[str]
    suffix: Optional[str]
    units: Optional[int]
    units_format: Optional[int]
    precision: Optional[int]
    override_value: Optional[str]
    suppress_zeroes: Optional[bool]


@dataclass
class DimensionStyle:
    thickness: Optional[float]
    arrow_length: Optional[float]
    text_position_mode: Optional[int]
    arrow_direction: Optional[str]
    extension_height: Optional[float]
    extension_offset: Optional[float]
    keep_text_aligned: bool
    text_frame: Optional[int]


@dataclass
class GrTextLayer:
    name: str = positional()
    knockout: bool = flag_boolean()


@dataclass(kw_only=True)
class GrText:
    text: str = positional()
    locked: Optional[bool]
    at: Vector2DWithRotation
    layer: Optional[GrTextLayer]
    uuid: Optional[str]
    hide: Optional[bool]
    effects: Optional[Effects]
    render_cache: Optional[RenderCache]
    tstamp: Optional[str]


@dataclass
class Dimension:
    type: str
    # locked: bool # free locked token in v6 and v7 formats
    layer: Optional[str]
    tstamp: Optional[str]
    uuid: Optional[str]
    pts: Optional[ShapeLineChain]
    height: Optional[float]
    leader_length: Optional[float]
    orientation: Optional[int]
    format: Optional[DimensionFormat]
    style: Optional[DimensionStyle]
    gr_text: Optional[GrText]


@dataclass
class Offset2d:
    xy: Vector2D


@dataclass
class Offset3d:
    xyz: Vector3D


@dataclass(kw_only=True)
class Drill:
    size_x: float = positional()
    size_y: Optional[float] = positional()  # if size_y is not set, it is = size_x (according to the kicad parser C++ source)
    oval: bool = flag_boolean()
    offset: Optional[Offset2d]


@dataclass
class PadOptions:
    clearance: Optional[str]
    anchor: Optional[str]


@dataclass
class GrArc:
    start: Optional[Vector2D]
    mid: Optional[Vector2D]
    end: Optional[Vector2D]
    stroke: Optional[Stroke]
    layer: Optional[str]
    locked: Optional[bool]
    uuid: Optional[str]
    layers: Optional[List[int]]
    solder_mask_margin: Optional[float]
    fill: Optional[str]
    tstamp: Optional[str]
    status: Optional[int]
    net: Optional[int]


@dataclass
class GrCircle:
    center: Optional[Vector2D]
    end: Optional[Vector2D]
    stroke: Optional[Stroke]
    fill: Optional[str]
    layer: Optional[str]
    layers: Optional[List[int]]
    solder_mask_margin: Optional[float]
    tstamp: Optional[str]
    locked: Optional[bool]
    uuid: Optional[str]
    status: Optional[int]
    net: Optional[int]


@dataclass
class GrCurve:
    pts: ShapeLineChain
    layer: Optional[str]
    layers: Optional[List[int]]
    solder_mask_margin: Optional[float]
    fill: Optional[str]
    tstamp: Optional[str]
    locked: Optional[bool]
    uuid: Optional[str]
    status: Optional[int]
    net: Optional[int]
    stroke: Optional[Stroke]


@dataclass
class GrRect:
    start: Optional[Vector2D]
    end: Optional[Vector2D]
    stroke: Optional[Stroke]
    fill: Optional[str]
    layer: Optional[str]
    layers: Optional[List[int]]
    solder_mask_margin: Optional[float]
    tstamp: Optional[str]
    locked: Optional[bool]
    uuid: Optional[str]
    status: Optional[int]
    net: Optional[int]


@dataclass
class GrBBox:
    start: Optional[Vector2D]
    end: Optional[Vector2D]
    width: Optional[float]
    layer: Optional[str]
    layers: Optional[List[int]]
    solder_mask_margin: Optional[float]
    stroke: Optional[Stroke]
    fill: Optional[str]
    tstamp: Optional[str]
    locked: Optional[bool]
    uuid: Optional[str]
    status: Optional[int]
    net: Optional[int]
    stroke: Optional[Stroke]

@dataclass
class GrLine:
    start: Optional[Vector2D]
    end: Optional[Vector2D]
    stroke: Optional[Stroke]
    layer: Optional[str]
    layers: Optional[List[int]]
    solder_mask_margin: Optional[float]
    fill: Optional[str]
    tstamp: Optional[str]
    locked: Optional[bool]
    uuid: Optional[str]
    status: Optional[int]
    net: Optional[int]


@dataclass
class GrVector:
    start: Optional[Vector2D]
    end: Optional[Vector2D]
    layer: Optional[str]
    layers: Optional[List[int]]
    solder_mask_margin: Optional[float]
    fill: Optional[str]
    tstamp: Optional[str]
    locked: Optional[bool]
    uuid: Optional[str]
    status: Optional[int]
    net: Optional[int]
    stroke: Optional[Stroke]


@dataclass
class GrPoly:
    pts: ShapeLineChain
    width: Optional[float]  # not sure why `.width` is here, but kicad adds it to kicad_pcb.footprint[108].pad[1].primitives.gr_poly[0].width when converting Altium files to kicad files
    stroke: Optional[Stroke]
    fill: Optional[str]
    layer: Optional[str]
    layers: Optional[List[int]]
    solder_mask_margin: Optional[float]
    tstamp: Optional[str]
    status: Optional[int]
    net: Optional[int]
    locked: Optional[bool]
    uuid: Optional[str]


@dataclass
class GrTextBox:
    text: str
    start: Optional[Vector2D]
    end: Optional[Vector2D]
    pts: Optional[ShapeLineChain]
    angle: Optional[float]
    stroke: Optional[Stroke]
    border: bool
    margins: Optional[Tuple[float, float, float, float]]
    layer: Optional[str]
    knockout: bool
    effects: Optional[Effects]
    render_cache: Optional[RenderCache]
    locked: Optional[bool]
    uuid: Optional[str]
    tstamp: Optional[str]


@dataclass
class Primitives:
    gr_arcs: List[GrArc]
    gr_circles: List[GrCircle]
    gr_curves: List[GrCurve]
    gr_rects: List[GrRect]
    gr_bboxes: List[GrBBox]
    gr_lines: List[GrLine]
    gr_vectors: List[GrVector]
    gr_polys: List[GrPoly]
    gr_texts: List[GrText]
    gr_text_boxes: List[GrTextBox]

    # todo fixme why are these here? I didn't add them
    width: Optional[float]
    fill: Optional[bool]

    @property
    def graphic_items(self):
        return list(chain.from_iterable(item for name, item in self.__dict__.items() if name.startswith('gr_')))

    def __len__(self):
        return len(self.graphic_items)

    def append(self, item, name):
        getattr(self, name).append(item)


@dataclass
class ViaTenting:
    front: bool = flag_boolean()
    back: bool = flag_boolean()


@dataclass
class PadstackLayer:
    shape: Optional[str]
    size: Optional[Vector2D]
    offset: Optional[Vector2D]
    rect_delta: Optional[Vector2D]
    roundrect_rratio: Optional[float]
    chamfer_ratio: Optional[float]
    chamfers: List[str]
    thermal_bridge_width: Optional[float]
    thermal_gap: Optional[float]
    thermal_bridge_angle: Optional[float]
    zone_connect: Optional[int]
    clearance: Optional[float]
    tenting: Optional[ViaTenting]
    options: Optional[PadOptions]
    primitives: Primitives


@dataclass
class Padstack:
    mode: str
    # todo fixme this should be converted to a List[...]
    layers: Dict[str, PadstackLayer]


@dataclass(kw_only=True)
class ZoneFill:
    yes: Optional[bool] = positional()
    mode: Optional[str]
    hatch_thickness: Optional[float]
    hatch_gap: Optional[float]
    hatch_orientation: Optional[float]
    hatch_smoothing_level: Optional[float]
    hatch_smoothing_value: Optional[float]
    hatch_border_algorithm: Optional[str]
    hatch_min_hole_area: Optional[float]
    arc_segments: Optional[int]
    thermal_gap: Optional[float]
    thermal_bridge_width: Optional[float]
    smoothing: Optional[str]
    radius: Optional[float]
    island_removal_mode: Optional[int]
    island_area_min: Optional[float]


@dataclass
class ZonePlacement:
    enabled: bool
    sheetname: Optional[str]
    component_class: Optional[str]
    group: Optional[str]


@dataclass
class ZoneKeepout:
    # todo fixme: add support to the parser for typing this as 'allowed' | 'not_allowed'
    tracks: str
    vias: str
    pads: str
    copperpour: str
    footprints: str


@dataclass
class ZoneAttrType:
    type: str


@dataclass
class ZoneAttr:
    teardrop: Optional[ZoneAttrType]


@dataclass
class Island:
    pass


@dataclass
class Polygon:
    layer: Optional[str]
    island: Optional[Island]
    ptss: List[ShapeLineChain]


@dataclass
class ZoneHatch:
    type: str = positional()
    value: float = positional()


@dataclass(kw_only=True)
class ZoneConnectPads:
    enable: Optional[bool] = positional()
    clearance: float


@dataclass
class Zone:
    net: Optional[int]
    net_name: Optional[str]
    layer: Optional[str]
    layers: List[str]
    uuid: Optional[str]
    hatch: Optional[ZoneHatch]
    priority: Optional[int]
    connect_pads: Optional[ZoneConnectPads]
    min_thickness: float
    filled_areas_thickness: Optional[bool]
    keepout: Optional[ZoneKeepout]
    placement: Optional[ZonePlacement]
    fill: Optional[ZoneFill]
    polygons: List[Polygon]
    # todo fixme this should be converted to a List[...]
    properties: Dict[str, ZoneLayerProperties]
    tstamp: Optional[str]
    name: Optional[str]
    attr: Optional[ZoneAttr]
    filled_polygons: List[Polygon]
    # todo fixme this should be converted to a List[...]
    fill_segments: Dict[int, List[Tuple[Vector2D, Vector2D]]]
    locked: Optional[bool]


@dataclass(kw_only=True)
class Model3D:
    filename: str = positional()
    at: Optional[Vector3D]
    hide: Optional[bool]
    opacity: Optional[float] = 1.0
    offset: Optional[Offset3d]
    scale: Optional[Offset3d]
    rotate: Optional[Offset3d]


@dataclass(kw_only=True)
class Group:
    name: Optional[str] = positional()
    locked: Optional[bool]
    uuid: Optional[str]
    lib_id: Optional[str]
    memberss: List[str]


@dataclass
class EmbeddedFile:
    name: str
    type: Optional[str]
    datas: List[str]
    checksum: str


@dataclass
class FpArc:
    locked: Optional[bool]
    start: Optional[Vector2D]
    mid: Optional[Vector2D]
    end: Optional[Vector2D]
    solder_mask_margin: Optional[float]
    stroke: Optional[Stroke]
    fill: Optional[str]
    layer: Optional[str]
    layers: List[int]
    tstamp: Optional[str]
    uuid: Optional[str]
    status: Optional[int]
    net: Optional[int]

    # todo fixme When we finish implementing the kicad file format upgrader
    #  remove the attribute angle and remove
    angle: Optional[float]
    def __post_init__(self):
        if self.angle is not None:
            # if the old kicad format is used (self.angle is specified)
            # fp_arcs's formats need to be upgraded to the new format
            # the old format:
            #     start=the center of the circle
            #     end=the start of the arc (on the edge of the circle)
            #     angle=the angle to go around the circle
            # the new format:
            #     start=the start of the arc (=end from the previous format)
            #     end=the end of the arc
            #     mid=the midpoint of the arc
            center = self.start
            arc_start = self.end
            arc_end = Vector2D(arc_start.x, arc_start.y)
            arc_end.rotate(center, -self.angle)
            arc_mid = Vector2D(arc_start.x, arc_start.y)
            arc_mid.rotate(center, -self.angle / 2)
            self.start = arc_start
            self.mid = arc_mid
            self.end = arc_end
            if self.angle < 0:
                # for some reason kicad's parser does this too
                self.start, self.end = self.end, self.start
            self.angle = None


@dataclass
class FpCircle:
    locked: Optional[bool]
    center: Optional[Vector2D]
    end: Optional[Vector2D]
    solder_mask_margin: Optional[float]
    stroke: Optional[Stroke]
    fill: Optional[str]
    layer: Optional[str]
    layers: List[int]
    tstamp: Optional[str]
    uuid: Optional[str]
    status: Optional[int]
    net: Optional[int]


@dataclass
class FpCurve:
    locked: Optional[bool]
    pts: ShapeLineChain
    solder_mask_margin: Optional[float]
    stroke: Optional[Stroke]
    fill: Optional[str]
    layer: Optional[str]
    layers: List[int]
    tstamp: Optional[str]
    uuid: Optional[str]
    status: Optional[int]
    net: Optional[int]


@dataclass
class FpRect:
    locked: Optional[bool]
    start: Optional[Vector2D]
    end: Optional[Vector2D]
    solder_mask_margin: Optional[float]
    stroke: Optional[Stroke]
    fill: Optional[str]
    layer: Optional[str]
    layers: List[int]
    tstamp: Optional[str]
    uuid: Optional[str]
    status: Optional[int]
    net: Optional[int]


@dataclass
class FpLine:
    locked: Optional[bool]
    start: Optional[Vector2D]
    end: Optional[Vector2D]
    solder_mask_margin: Optional[float]
    stroke: Optional[Stroke]
    fill: Optional[str]
    layer: Optional[str]
    layers: List[int]
    tstamp: Optional[str]
    uuid: Optional[str]
    status: Optional[int]
    net: Optional[int]


@dataclass
class FpPoly:
    locked: Optional[bool]
    pts: ShapeLineChain
    solder_mask_margin: Optional[float]
    stroke: Optional[Stroke]
    fill: Optional[str]
    layer: Optional[str]
    layers: List[int]
    tstamp: Optional[str]
    uuid: Optional[str]
    status: Optional[int]
    net: Optional[int]


@dataclass(kw_only=True)
class FpText:
    type: str = positional()
    text: str = positional()
    locked: Optional[bool]
    at: Vector2DWithRotation
    stroke: Optional[Stroke]
    unlocked: Optional[bool]
    layer: Optional[str]
    knockout: Optional[bool]
    hide: Optional[bool]
    uuid: Optional[str]
    effects: Optional[Effects]
    render_cache: Optional[RenderCache]
    tstamp: Optional[str]


@dataclass(kw_only=True)
class FpTextBox:
    text: str = positional()
    locked: Optional[bool]
    start: Optional[Vector2D]
    end: Optional[Vector2D]
    margins: Optional[Margins]
    angle: Optional[float]
    layer: Optional[str]
    uuid: Optional[str]
    effects: Optional[Effects]
    border: Optional[bool]
    stroke: Optional[Stroke]
    render_cache: Optional[RenderCache]
    pts: Optional[ShapeLineChain]
    tstamp: Optional[str]
    knockout: Optional[bool]


@dataclass
class Track:
    #type: str = "segment"  # todo fixme what??
    start: Vector2D
    end: Vector2D
    width: float
    locked: Optional[bool]
    layer: Optional[str]
    layers: List[str]
    solder_mask_margin: Optional[float]
    net: Optional[int]
    tstamp: Optional[str]
    uuid: str
    status: Optional[int]


@dataclass
class ArcTrack:
    locked: Optional[bool]
    start: Vector2D
    mid: Vector2D
    end: Vector2D
    width: float
    layer: Optional[str]
    layers: List[str]
    solder_mask_margin: Optional[float]
    net: Optional[int]
    tstamp: Optional[str]
    uuid: Optional[str]
    status: Optional[int]


@dataclass(kw_only=True)
class Via:
    blind: bool = flag_boolean()
    buried: bool = flag_boolean()
    micro: bool = flag_boolean()
    at: Vector2D
    size: float
    drill: float
    layers: List[str]
    locked: Optional[bool]
    tenting: Optional[ViaTenting]
    net: Optional[int]
    remove_unused_layers: Optional[bool]
    keep_end_layers: Optional[bool]
    start_end_only: Optional[bool]
    zone_layer_connections: List[str]
    padstack: Optional[Padstack]
    teardrops: Optional[TeardropParameters]
    covering: Optional[ViaTenting]
    plugging: Optional[ViaTenting]
    filling: Optional[bool]
    capping: Optional[bool]
    tstamp: Optional[str]
    uuid: Optional[str]
    status: Optional[int]
    free: Optional[bool]


@dataclass
class Target:
    shape: str
    at: Vector2DWithRotation
    size: float
    width: float
    layer: str
    tstamp: Optional[str]
    uuid: Optional[str]


@dataclass
class Generator:
    uuid: str
    type: str
    name: Optional[str]
    locked: bool
    layer: Optional[str]
    memberss: List[str]
    # todo fixme this should be converted to a List[...]
    properties: Dict[str, Union[bool, float, str, Vector2D, ShapeLineChain]]


@dataclass
class LayerList:
    layer_infos: List[Layer]


@dataclass(kw_only=True)
class Pad:
    _custom_pad_constituent_bboxes: List[BoundingBox] | None = None  # only used for visual debugging. |None so existing subcircuits created before this was added don't break
    _bounding_box: BoundingBox = field(default_factory=lambda: BoundingBox(0, 0, 0, 0))
    number: str = positional()
    type: str = positional()  # allowed values: thru_hole, smd, connect, or np_thru_hole
    shape: str = positional()  # allowed values: circle, rectangle, roundrect, oval, trapezoid or custom
    at: Vector2DWithRotation
    size: Vector2D
    rect_delta: Optional[Vector2D]
    drill: Optional[Drill]
    layers: List[str]
    roundrect_rratio: Optional[float]
    net: Optional[Net]
    remove_unused_layers: Optional[bool]
    die_length: Optional[float]
    die_delay: Optional[float]
    solder_mask_margin: Optional[float]
    solder_paste_margin: Optional[float]
    solder_paste_margin_ratio: Optional[float]
    clearance: Optional[float]
    teardrops: Optional[TeardropParameters]
    zone_connect: Optional[int]
    thermal_bridge_width: Optional[float]
    thermal_bridge_angle: Optional[float]
    thermal_gap: Optional[float]
    chamfer_ratio: Optional[float]
    chamfers: List[str]
    pinfunction: Optional[str]
    pintype: Optional[str]
    property: Optional[str]
    options: Optional[PadOptions]
    padstack: Optional[Padstack]
    primitives: Optional[Primitives]
    keep_end_layers: Optional[bool]
    tenting: Optional[ViaTenting]
    zone_layer_connections: List[str]
    locked: Optional[bool]
    tstamp: Optional[str]
    uuid: Optional[str]

    def __post_init__(self):
        """Initialize bounding box after dataclass initialization."""
        self.compute_bounding_box()

    def compute_bounding_box(self):
        bounding_box = BoundingBox(0, 0, 0, 0)
        if self.shape == 'custom' and self.primitives is not None:
            self._custom_pad_constituent_bboxes = [
                get_element_bbox(element).rotate(self.at.rot).translate(self.at.x, self.at.y)
                for element in self.primitives.graphic_items
                if not isinstance(element, GrText) and not isinstance(element, GrTextBox)
            ]
            self._bounding_box = sum(self._custom_pad_constituent_bboxes)
        else:
            bounding_box = BoundingBox(self.at.x - self.size.x / 2, self.at.y - self.size.y / 2, self.size.x, self.size.y)
            self._custom_pad_constituent_bboxes = [bounding_box.rotate(self.at.rot, self.at)]
            self._bounding_box = bounding_box.rotate(self.at.rot, self.at)


@dataclass
class EmbeddedFiles:
    files: List[EmbeddedFile]


@dataclass(kw_only=True)
class Footprint(DataclassSerializerMixin, SexprMixin):
    _custom_pad_constituent_bboxes: List[BoundingBox] | None = None  # this attribute is only for visual debugging. |None so existing subcircuits created before this was added don't break
    _all_bboxes: List[BoundingBox] | None = None  # this attribute is only for visual debugging. |None so existing subcircuits created before this was added don't break
    _bounding_box: BoundingBox = None  # not |None because it's set in __post_init__, but setting to None so we can differentiate if from a value that may or may not have been passed as an arg
    _reference: FpText | None = None
    name: str = positional()
    version: Optional[int]
    generator: Optional[str]
    generator_version: Optional[str]
    locked: Optional[bool]
    placed: Optional[bool]
    layer: str  # "F.Cu" | "B.Cu"
    tedit: Optional[int]
    tstamp: Optional[str]
    uuid: str = field(default_factory=lambda: str(uuid4()))
    at: Optional[Vector2DWithRotation]
    descr: Optional[str]
    tags: Optional[str]
    properties: List[Property]
    path: Optional[str]
    sheetname: Optional[str]
    sheetfile: Optional[str]
    autoplace_cost90: Optional[int]
    autoplace_cost180: Optional[int]
    private_layers: List[str]
    net_tie_pad_groups: List[str]
    duplicate_pad_numbers_are_jumpers: Optional[bool]
    jumper_pad_groups: List[List[str]]
    solder_mask_margin: Optional[float]
    solder_paste_margin: Optional[float]
    solder_paste_margin_ratio: Optional[float]
    clearance: Optional[float]
    zone_connect: Optional[int]
    thermal_width: Optional[float]
    thermal_gap: Optional[float]
    attrs: List[str]
    tables: List[Table]
    images: List[ReferenceImage]
    dimensions: List[Dimension]
    groups: List[Group]
    component_classes: List[str]
    fp_arcs: List[FpArc]
    fp_circles: List[FpCircle]
    fp_curves: List[FpCurve]
    fp_rects: List[FpRect]
    fp_lines: List[FpLine]
    fp_polys: List[FpPoly]
    fp_texts: List[FpText]
    fp_text_boxes: List[FpTextBox]
    pads: List[Pad]
    zones: List[Zone]
    embedded_fonts: Optional[bool]
    embedded_files: Optional[EmbeddedFiles]
    models: List[Model3D]
    _preserve_interleaved_order: List[str] = field(default_factory=lambda: ['fp_arcs', 'fp_circles', 'fp_curves', 'fp_rects', 'fp_lines', 'fp_polys', 'fp_texts', 'fp_text_boxes'])

    def __post_init__(self):
        """Initialize bounding box after dataclass initialization."""
        # passing self._bounding_box as an arg is not required since it's computed,
        # but it may be provided if this dataclass was serialized and is being reparsed,
        # so check to make sure it is correct. And if it was not provided (ex. the first time), then calculate it
        bbox_passed_as_argument = self._bounding_box
        self.compute_bounding_box()
        # now self._bounding_box is set based on the ground truth computation
        # todo fixme: uncomment this before opening a PR, and leave it in the final code as a safety check
        if bbox_passed_as_argument is not None and bbox_passed_as_argument != self._bounding_box:
             raise Exception(f"A bounding box {bbox_passed_as_argument} was passed as an argument, "
                             f"but does not match the newly computed bounding box {self._bounding_box} "
                             f"that's based on what's truly in this footprint.")

    @property
    def footprint_items(self):
        """Get the footprint items that are children of the footprint such as lines or arcs.
        The function to get the items that are children of board is a function of the board class"""
        return list(chain.from_iterable(item for name, item in self.__dict__.items() if name.startswith('fp_')))
   
    def compute_bounding_box(self):
        """Compute the bounding box for the footprint based on its graphic items."""
        fp_bboxes = [
            get_element_bbox(element)
            for element in self.footprint_items
            if not isinstance(element, FpText) and not isinstance(element, FpTextBox)
        ]
        pad_bboxes = [element._bounding_box for element in self.pads]
        all_bounding_boxes = fp_bboxes + pad_bboxes
        aggregated_bbox = sum(all_bounding_boxes)
        # only for debugging
        self._all_bboxes = [bbox.translate(self.at.x, self.at.y).rotate(self.at.rot if self.at.rot is not None else 0, rotation_center=self.at)
                            for bbox
                            in fp_bboxes] + [bbox.translate(self.at.x, self.at.y).rotate(-self.at.rot if self.at.rot is not None else 0).rotate(self.at.rot if self.at.rot is not None else 0, rotation_center=self.at)
                            for bbox
                            in pad_bboxes]
        self._custom_pad_constituent_bboxes = []
        for pad in self.pads:
            for bbox in pad._custom_pad_constituent_bboxes:
                self._custom_pad_constituent_bboxes.append(
                    bbox.translate(self.at.x, self.at.y).rotate(-self.at.rot if self.at.rot is not None else 0).rotate(self.at.rot if self.at.rot is not None else 0, rotation_center=self.at)
                )

        self._bounding_box = sum(self._all_bboxes)

    def set_position(self, position: Vector2DWithRotation):
        """Set the position of the footprint and update its children's positions.

        Args:
            position (Position): The new position of the footprint.
        """
        delta = position - self.at
        self.at = position
        for pad in self.pads:
            pad.at.rot = normalize_angle(pad.at.rot + delta.rot)
            pad.compute_bounding_box()

        self.compute_bounding_box()
    
    def __eq__(self, other):
        if isinstance(other, Footprint):
            return self.uuid == other.uuid
        return False

    def __hash__(self):
        return hash(self.uuid)

    def add_fp_item(self, fp_item: FpText | FpTextBox | FpLine | FpRect | FpCircle | FpPoly | FpCurve | FpArc):
        """Adds a footprint graphic item to the footprint."""
        try:
            if isinstance(fp_item, FpText):
                self.fp_text.append(fp_item)
            elif isinstance(fp_item, FpTextBox):
                self.fp_text_box.append(fp_item)
            elif isinstance(fp_item, FpLine):
                self.fp_line.append(fp_item)
            elif isinstance(fp_item, FpRect):
                self.fp_rect.append(fp_item)
            elif isinstance(fp_item, FpCircle):
                self.fp_circle.append(fp_item)
            elif isinstance(fp_item, FpPoly):
                self.fp_poly.append(fp_item)
            elif isinstance(fp_item, FpCurve):
                self.fp_curve.append(fp_item)
            elif isinstance(fp_item, FpArc):
                self.fp_arc.append(fp_item)
        except TypeError:
            raise TypeError(f"Unsupported footprint item type: {type(fp_item).__name__}")

    def get_directly_connected_footprints(
        self, footprints: Iterable["Footprint"]
    ) -> Set["Footprint"]:
        """Returns a list of the footprints that are directly connected to self"""
        directly_connected = set()
        footprint_nets = set()
        for pad in self.pads:
            net = pad.net
            if net is None:
                continue
            if net.name == "" or net.name == "GND":
                continue
            footprint_nets.add((net.name,))

        for other in footprints:
            if other == self:
                continue

            for pad in other.pads:
                net = pad.net
                if net is None:
                    continue
                if net.name == "" or net.name == "GND":
                    continue
                if (net.name,) in footprint_nets:
                    directly_connected.add(other)

        return directly_connected

    def get_property(self, key: str) -> str | None:
        """Returns the value of the property with the given key."""
        for prop in self.properties:
            if prop.name == key:
                return prop.value
        return None


@dataclass
class Board(DataclassSerializerMixin, SexprMixin):
    version: int
    generator: Optional[str]
    generator_version: Optional[str]
    general: Optional[General]
    paper: Optional[PageInfo]
    title_block: Optional[TitleBlock]
    layers: List[LayerList]
    setup: Optional[Setup]
    properties: List[Property]
    nets: List[Net]
    net_classes: List[NetClass]
    images: List[ReferenceImage]
    tables: List[Table]
    footprints: List[Footprint]
    generated: List[Generator]
    targets: List[Target]
    gr_arcs: List[GrArc]
    gr_circles: List[GrCircle]
    gr_curves: List[GrCurve]
    gr_rects: List[GrRect]
    gr_bboxs: List[GrBBox]
    gr_lines: List[GrLine]
    gr_vectors: List[GrVector]
    gr_polys: List[GrPoly]
    gr_texts: List[GrText]
    gr_text_boxes: List[GrTextBox]
    segments: List[Track]
    vias: List[Via]
    arcs: List[ArcTrack]
    dimensions: List[Dimension]
    zones: List[Zone]
    groups: List[Group]
    embedded_fonts: Optional[bool]
    embedded_files: Optional[EmbeddedFiles]

    _preserve_interleaved_order: List[str] = field(default_factory=lambda: ['segments', 'arcs', 'vias',
                                   'dimensions',
                                   'gr_arcs', 'gr_circles', 'gr_curves', 'gr_rects', 'gr_bboxs', 'gr_lines', 'gr_vectors', 'gr_polys', 'gr_texts', 'gr_text_boxes'])


    @property
    def locked_components(self) -> Set[Footprint]:
        """Returns a list of components that have locked position."""
        return {footprint for footprint in self.footprints if footprint.locked}
  
    def get_padded_board_bbox(self, padding: float = 5) -> BoundingBox:
        if not self.footprints:
            return BoundingBox(0, 0, 0, 0)

        bbox = sum(footprint._bounding_box for footprint in self.footprints)
        bbox.x -= padding
        bbox.y -= padding
        bbox.width += 2 * padding
        bbox.height += 2 * padding

        return bbox

    def replace_footprint(self, new_footprint: Footprint) -> bool:
        """Replaces an object in the list with the new_object based on matching uuid."""
        for index, footprint in enumerate(self.footprints):
            if footprint.uuid == new_footprint.uuid:
                self.footprints[index] = new_footprint
                return True
        return False

    def add_gr_item(self, gr_item: GrText | GrTextBox | GrLine | GrRect | GrCircle | GrPoly | GrCurve | GrArc):
        """Adds a graphic item to the board."""
        try:
            if isinstance(gr_item, GrText):
                self.gr_text.append(gr_item)
            elif isinstance(gr_item, GrTextBox):
                self.gr_text_box.append(gr_item)
            elif isinstance(gr_item, GrLine):
                self.gr_line.append(gr_item)
            elif isinstance(gr_item, GrRect):
                self.gr_rect.append(gr_item)
            elif isinstance(gr_item, GrCircle):
                self.gr_circle.append(gr_item)
            elif isinstance(gr_item, GrPoly):
                self.gr_poly.append(gr_item)
            elif isinstance(gr_item, GrCurve):
                self.gr_curve.append(gr_item)
            elif isinstance(gr_item, GrArc):
                self.gr_arc.append(gr_item)
        except TypeError:
            raise TypeError(f"Unsupported graphic item type: {type(gr_item).__name__}")


def get_element_bbox(
    element: "GraphicItem",
) -> BoundingBox:
    """Calculate the bounding box for a given PCB element.

    Args:
        element (Union[FpRect, FpArc, FpLine, FpPoly, FpCurve, FpCircle]): The PCB element for which to calculate the bounding box.
        transform (Optional[Position]): Optional transformation to apply to the bounding box.

    Returns:
        BoundingBox: The bounding box of the given element.
    """
    # When a graphical item has a stroke width, include the stroke width in the calculation of the bounding box,
    # but if the graphical item is a type that does not have a stroke width,
    # set the stroke width to 0 to keep the calculation code the same
    if hasattr(element, 'stroke') and element.stroke is not None and element.stroke.width is not None:
        stroke_width = element.stroke.width
    elif hasattr(element, 'width'):
        stroke_width = element.width
    else:
        # This is a default stroke width value (optional in itself) for elements starting from KiCAD v7,
        # so it's preferable over raising an error
        stroke_width = 0
    half_stroke = stroke_width / 2

    if isinstance(element, FpRect) or isinstance(element, GrRect):
        min_x = min(element.start.x, element.end.x)
        min_y = min(element.start.y, element.end.y)
        width = abs(element.end.x - element.start.x)
        height = abs(element.end.y - element.start.y)
        bounding_box = BoundingBox(
            min_x - half_stroke, min_y - half_stroke, width + stroke_width, height + stroke_width
        )

    elif isinstance(element, FpCircle) or isinstance(element, GrCircle):
        cx, cy = element.center.x, element.center.y
        radius = abs(element.end.x - element.center.x)
        bounding_box = BoundingBox(
            cx - radius - half_stroke, cy - radius - half_stroke, radius * 2 + stroke_width, radius * 2 + stroke_width
        )

    elif isinstance(element, FpArc) or isinstance(element, GrArc):
        bounding_box = get_arc_bounding_box(element.start, element.mid, element.end)
        bounding_box = BoundingBox(
            bounding_box.x - half_stroke,
            bounding_box.y - half_stroke,
            bounding_box.width + stroke_width,
            bounding_box.height + stroke_width,
        )

    elif isinstance(element, FpLine) or isinstance(element, GrLine):
        min_x = min(element.start.x, element.end.x)
        min_y = min(element.start.y, element.end.y)
        max_x = max(element.end.x, element.start.x)
        max_y = max(element.end.y, element.start.y)
        width = max_x - min_x
        height = max_y - min_y
        bounding_box = BoundingBox(
            min_x - half_stroke, min_y - half_stroke, width + stroke_width, height + stroke_width
        )

    elif (
        isinstance(element, FpPoly)
        or isinstance(element, FpCurve)
        or isinstance(element, GrPoly)
        or isinstance(element, GrCurve)
    ):
        all_x_coords = []
        all_y_coords = []
        arc_bboxes = []

        for point in element.pts.xys:
            all_x_coords.append(point.x)
            all_y_coords.append(point.y)

        for arc in element.pts.arcs:
            arc_bbox = get_arc_bounding_box(arc.start, arc.mid, arc.end)
            arc_bboxes.append(arc_bbox)
            all_x_coords.extend([arc_bbox.x, arc_bbox.x + arc_bbox.width])
            all_y_coords.extend([arc_bbox.y, arc_bbox.y + arc_bbox.height])

        if not all_x_coords:
            return BoundingBox(0, 0, 0, 0)

        min_x = min(all_x_coords)
        min_y = min(all_y_coords)
        max_x = max(all_x_coords)
        max_y = max(all_y_coords)

        bounding_box = BoundingBox(
            min_x - half_stroke, min_y - half_stroke, max_x - min_x + stroke_width, max_y - min_y + stroke_width
        )

    else:
        return BoundingBox(0, 0, 0, 0)

    return bounding_box


GraphicItem = Union[FpArc, FpLine, FpPoly, FpCurve, FpRect, GrArc, GrLine, GrPoly, GrCurve, GrBBox, GrTextBox, GrVector, GrCircle, GrRect, GrText, GrTextBox]

if __name__ == '__main__':
    from pathlib import Path
    board = Board.from_file('/tmp/project.kicad_pcb')

    from autopcb.datatypes.common import Vector2DWithRotation
    import json
    footprint = Footprint.from_json(json.loads(Path('/tmp/a').read_text()))

    newRotation = footprint.at.rot + 90
    footprint.set_position(Vector2DWithRotation(x=footprint.at.x, y=footprint.at.y, rot=newRotation))
    newRotation = footprint.at.rot - 90
    footprint.set_position(Vector2DWithRotation(x=footprint.at.x, y=footprint.at.y, rot=newRotation))

    Path('/tmp/out.kicad_pcb').write_text(board.to_sexpr('kicad_pcb'))
    pass
