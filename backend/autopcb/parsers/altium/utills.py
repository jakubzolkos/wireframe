import math
import uuid
from typing import Any, Callable, List

from construct import Container, EnumIntegerString
from kicad_modification.datatypes import Position
from kicad_modification.items import Arc, FpItem, GrArc, GrCircle, GrItem, GrLine, GrPoly, Zone
from kicad_modification.parsers.altium.converters import convert_altium_position
from kicad_modification.parsers.altium.enums import ALTIUM_LAYER, ALTIUM_PAD_SHAPE, ALTIUM_PAD_SHAPE_ALT, KICAD_LAYER
from kicad_modification.parsers.altium.mappings import altium_string_to_enum_layer_map, altium_to_kicad_layer_map
from kicad_modification.parsers.altium.readers import AltiumVertex
from kicad_modification.utils import distance
from kiutils.items.brditems import Stackup
from kiutils.items.common import Stroke
from kiutils.items.zones import Hatch


def get_altium_layer_value(altium_layer: EnumIntegerString | ALTIUM_LAYER | int | str) -> Callable[[], Any] | int | Any:
    """
    Converts an Altium layer input (various types) to its integer value.
    """
    if isinstance(altium_layer, EnumIntegerString):
        return int(altium_layer)
    elif isinstance(altium_layer, ALTIUM_LAYER):
        return altium_layer.value
    elif isinstance(altium_layer, str):
        return altium_string_to_enum_layer_map.get(altium_layer, ALTIUM_LAYER.UNKNOWN).value
    elif isinstance(altium_layer, int):
        return altium_layer
    else:
        return ALTIUM_LAYER.UNKNOWN.value


def is_internal_altium_plane(altium_layer: EnumIntegerString | ALTIUM_LAYER | int | str) -> bool:
    """Checks if an Altium layer is an internal plane"""
    layer = get_altium_layer_value(altium_layer)
    return ALTIUM_LAYER.INTERNAL_PLANE_1.value <= layer <= ALTIUM_LAYER.INTERNAL_PLANE_16.value


def is_altium_copper_layer(altium_layer: EnumIntegerString | ALTIUM_LAYER | int | str) -> bool:
    """Checks if an Altium layer is copper"""
    layer = get_altium_layer_value(altium_layer)
    return ALTIUM_LAYER.TOP_LAYER.value <= layer <= ALTIUM_LAYER.BOTTOM_LAYER.value


def get_remaining_bytes(ctx: Container):
    """Returns the number of remaining bytes in a byte stream"""
    current_position = ctx._io.tell()
    ctx._io.seek(0, 2)
    total_size = ctx._io.tell()
    ctx._io.seek(current_position)
    return total_size - current_position


def get_default_stackup(layercount: int | None = None) -> Stackup:
    """Returns a default stackup configuration for a KiCAD board"""
    pass


def get_kicad_layer(altium_layer: EnumIntegerString | ALTIUM_LAYER | int | str) -> KICAD_LAYER:
    """Converts an Altium layer to its KiCAD equivalent."""

    # Depending on the origin, Altium layer can be represented differently
    layer = altium_layer
    if isinstance(altium_layer, EnumIntegerString):
        layer = ALTIUM_LAYER(int(altium_layer))
    elif isinstance(altium_layer, int):
        layer = ALTIUM_LAYER(altium_layer)
    elif isinstance(altium_layer, str):
        # Obtained from property dictionary
        layer = altium_string_to_enum_layer_map.get(layer, ALTIUM_LAYER.UNKNOWN)

    return altium_to_kicad_layer_map.get(layer, KICAD_LAYER.Undefined_Layer)


def get_altium_layer_from_name(altium_layer_name: str) -> ALTIUM_LAYER:
    return altium_string_to_enum_layer_map.get(altium_layer_name, ALTIUM_LAYER.UNKNOWN)


def get_position(vertex: Position | Container) -> Position:
    position = vertex
    if not isinstance(vertex, Position):
        position = convert_altium_position(vertex)

    return position


def create_arc(center: Position, radius: float, start_angle_deg: float, sweep_angle_deg: float) -> Arc:
    """
    Create an Arc object given the circle center, radius, a start angle,
    and a sweep angle (in degrees).
      - start angle (absolute)
      - sweep angle (relative, could be positive or negative)
    """
    start_angle_rad = math.radians(start_angle_deg)
    sweep_angle_rad = math.radians(sweep_angle_deg)
    mid_angle_rad = start_angle_rad + 0.5 * sweep_angle_rad
    end_angle_rad = start_angle_rad + sweep_angle_rad

    arc_start = Position(center.X + math.cos(start_angle_rad) * radius, center.Y - math.sin(start_angle_rad) * radius)
    arc_mid = Position(center.X + math.cos(mid_angle_rad) * radius, center.Y - math.sin(mid_angle_rad) * radius)
    arc_end = Position(center.X + math.cos(end_angle_rad) * radius, center.Y - math.sin(end_angle_rad) * radius)
    return Arc(arc_start, arc_mid, arc_end)


def get_shape_line_chain_from_altium_vertices(vertices: List[Container | AltiumVertex]) -> List[Position | Arc]:
    shape_line_chain: List[Position | Arc] = []

    for vertex in vertices:
        # Convert vertex.position to a Position
        vertex_position = get_position(vertex.position)

        if hasattr(vertex, "is_round") and vertex.is_round:
            # We have an arc

            # Compute total sweep angle = (end_angle - start_angle)
            angle = vertex.end_angle - vertex.start_angle

            # If negative, add 360. If >= 360, subtract 360.
            # This ensures angle is between 0 and 360 but does not preserve sign.
            # If you need clockwise arcs, handle negative angles differently.
            if angle < 0:
                angle += 360
            elif angle >= 360:
                angle -= 360

            # Precompute start and end points, for checking "small arcs"
            startrad = math.radians(vertex.start_angle)
            endrad = math.radians(vertex.end_angle)

            center = get_position(vertex.center)
            arc_start = Position(
                center.X + math.cos(startrad) * vertex.radius, center.Y - math.sin(startrad) * vertex.radius
            )
            arc_end = Position(center.X + math.cos(endrad) * vertex.radius, center.Y - math.sin(endrad) * vertex.radius)

            # Decide if arc is extremely short
            is_short = distance(arc_start, arc_end) < 0.001 or abs(angle) < 0.2

            # Determine which point is closer to vertex_position
            # (this is presumably for the correct connecting order).
            dist_start = distance(arc_start, vertex_position)
            dist_end = distance(arc_end, vertex_position)

            if dist_start < dist_end:
                # The arc starts from arc_start -> arc_end
                if not is_short:
                    arc_obj = create_arc(center, vertex.radius, vertex.start_angle, angle)
                    shape_line_chain.append(arc_obj)
                else:
                    # If too short, just add the points as line segments
                    shape_line_chain.append(arc_start)
                    shape_line_chain.append(arc_end)
            else:
                # The arc starts from arc_end -> arc_start
                if not is_short:
                    # Notice we pass a negative sweep or reversed angles
                    # if you truly want an arc in the opposite direction.
                    # One approach is flipping the sign: create_arc(..., vertex.end_angle, -angle).
                    arc_obj = create_arc(center, vertex.radius, vertex.end_angle, -angle)
                    shape_line_chain.append(arc_obj)
                else:
                    shape_line_chain.append(arc_end)
                    shape_line_chain.append(arc_start)

        else:
            # Not an arc, just a vertex (Position)
            shape_line_chain.append(vertex_position)

    return shape_line_chain


def get_board_outline(altium_vertices: List[AltiumVertex]) -> List[GrLine | GrArc]:
    """Creates a segment list for a board outline from a list of Altium vertices"""
    board_outline = []
    shape_line_chain = get_shape_line_chain_from_altium_vertices(altium_vertices)
    i = 0
    while i < len(shape_line_chain):
        obj = shape_line_chain[i]
        try:
            if isinstance(obj, Arc):
                arc = GrArc(
                    start=obj.start, mid=obj.mid, end=obj.end, layer="Edge.Cuts", tstamp=str(uuid.uuid4()), width=0.05
                )
                board_outline.append(arc)

            elif isinstance(obj, Position):
                if isinstance(shape_line_chain[i + 1], Position):
                    segment_end = shape_line_chain[i + 1]
                else:
                    segment_end = shape_line_chain[i + 1].start

                segment = GrLine(
                    layer="Edge.Cuts",
                    start=obj,
                    end=segment_end,
                    tstamp=str(uuid.uuid4()),
                    stroke=Stroke(0.05, "solid"),
                )
                board_outline.append(segment)

            i += 1
        except IndexError:
            return board_outline
    return board_outline


def get_shape_as_keepout_region(altium_component: Container, polygon_shape: FpItem | GrItem) -> Zone:
    zone = Zone()
    zone.hatch = Hatch("edge", 0.5)
    for layer in get_kicad_layers_to_iterate(altium_component.layer):
        zone.layers.append(layer.name)

    # Shape should be transformed into a zone polygon and added to the zone

    return zone


def get_kicad_layers_to_iterate(altium_layer: EnumIntegerString | ALTIUM_LAYER | str | int):
    """
    Retrieves a list of KiCad layers corresponding to an Altium layer. This usually reduces to one layer, but
    Altium multi layer type or keep out layer pertain to many copper layers.
    """
    layer = ALTIUM_LAYER(get_altium_layer_value(altium_layer))

    if layer == ALTIUM_LAYER.MULTI_LAYER or layer == ALTIUM_LAYER.KEEP_OUT_LAYER:
        return [layer for layer in KICAD_LAYER if KICAD_LAYER.is_copper_layer(layer)]

    kicad_layer = get_kicad_layer(altium_layer)
    if kicad_layer == KICAD_LAYER.Undefined_Layer:
        kicad_layer = KICAD_LAYER.Eco1_User

    return [kicad_layer]


def get_closed_altium_vertex_chain(positions: List[Container]) -> List[Position]:
    """
    Creates a closed chain from a list of positions by converting them to AutoPCB representation and
    appending the starting position to the end of the chain.
    """
    if not positions:
        raise ValueError("The positions list cannot be empty.")

    starting_point = convert_altium_position(positions[0])
    return [starting_point] + [convert_altium_position(pos) for pos in positions[1:]] + [starting_point]


def convert_altium_pad(altium_pad: Container):
    """Converts an Altium pad to KiCad"""
    layer = get_kicad_layer(altium_pad.layer)
    if layer == KICAD_LAYER.Undefined_Layer:
        layer = KICAD_LAYER.Eco1_User.name
    else:
        layer = layer.name

    pad_topshape = ALTIUM_PAD_SHAPE(int(altium_pad.topshape))
    alt_shape = (
        ALTIUM_PAD_SHAPE_ALT(int(altium_pad.size_and_shape.alt_shape[0]))
        if altium_pad.size_and_shape is not None
        else None
    )

    match pad_topshape:
        case ALTIUM_PAD_SHAPE.RECT:
            custom_shape = GrPoly()
            custom_shape.fill = "solid"
            custom_shape.layer = layer
            custom_shape.stroke = Stroke(0, "default")
            position = convert_altium_position(altium_pad.position)
            custom_shape.coordinates = [
                position + Position(altium_pad.topsize.x / 2, altium_pad.topsize.y / 2),
                position + Position(altium_pad.topsize.x / 2, -altium_pad.topsize.y / 2),
                position + Position(-altium_pad.topsize.x / 2, -altium_pad.topsize.y / 2),
                position + Position(-altium_pad.topsize.x / 2, altium_pad.topsize.y / 2),
            ]

            if altium_pad.direction != 0:
                for index, vertex in enumerate(custom_shape.coordinates):
                    custom_shape.coordinates[index].rotate(Position(position.X, position.Y, altium_pad.direction))

        case ALTIUM_PAD_SHAPE.CIRCLE:
            if alt_shape == ALTIUM_PAD_SHAPE_ALT.ROUNDRECT:
                corner_radius = altium_pad.size_and_shape.cornerradius[0]
                offset = min(altium_pad.topsize.x, altium_pad.topsize.y) * corner_radius / 200

                if corner_radius < 100:
                    offset_x = altium_pad.topsize.x / 2 - offset
                    offset_y = altium_pad.topsize.y / 2 - offset
                    custom_shape = GrPoly()
                    custom_shape.layer = layer
                    custom_shape.fill = "solid"
                    position = convert_altium_position(altium_pad.position)
                    custom_shape.coordinates = [
                        position + Position(offset_x, offset_y),
                        position + Position(offset_x, -offset_y),
                        position + Position(-offset_x, -offset_y),
                        position + Position(-offset_x, offset_y),
                    ]
                    custom_shape.stroke = Stroke(offset * 2, "solid")

                elif altium_pad.topsize.x == altium_pad.topsize.y:
                    # Circle
                    center = convert_altium_position(altium_pad.position)
                    custom_shape = GrCircle()
                    custom_shape.layer = layer
                    custom_shape.fill = "solid"
                    custom_shape.center = center
                    custom_shape.end = center - Position(0, altium_pad.topsize.x / 4)
                    custom_shape.stoke = Stroke(altium_pad.topsize.x / 2, "solid")

                elif altium_pad.topsize.x < altium_pad.topsize.y:
                    # Short vertical line
                    custom_shape = GrLine()
                    custom_shape.layer = layer
                    point_offset = Position(0, altium_pad.topsize.x / 2 - altium_pad.topsize.y / 2)
                    custom_shape.start = convert_altium_position(altium_pad.position) + point_offset
                    custom_shape.end = convert_altium_position(altium_pad.position) - point_offset
                    custom_shape.stroke = Stroke(offset * 2, "solid")

                else:
                    # Short horizontal line
                    custom_shape = GrLine()
                    custom_shape.layer = layer
                    point_offset = Position(altium_pad.topsize.x / 2 - altium_pad.topsize.y / 2, 0)
                    custom_shape.start = convert_altium_position(altium_pad.position) + point_offset
                    custom_shape.end = convert_altium_position(altium_pad.position) - point_offset
                    custom_shape.stroke = Stroke(offset * 2, "solid")

                if altium_pad.direction != 0:
                    """ROTATE ELEMENT"""
                    pass

            elif altium_pad.topsize.x == altium_pad.topsize.y:
                # Filled circle
                center = convert_altium_position(altium_pad.position)
                custom_shape = GrCircle()
                custom_shape.layer = layer
                custom_shape.fill = "solid"
                custom_shape.center = center
                custom_shape.end = center - Position(0, altium_pad.topsize.x / 4)
                custom_shape.stroke = Stroke(altium_pad.topsize.x / 2, "solid")

            else:
                custom_shape = GrLine()
                custom_shape.layer = layer
                custom_shape.stroke = Stroke(min(altium_pad.topsize.x, altium_pad.topsize.y), "solid")
                position = convert_altium_position(altium_pad.position)

                if altium_pad.topsize.x < altium_pad.topsize.y:
                    offset = Position(0, altium_pad.topsize.y / 2 - altium_pad.topsize.x / 2)
                    custom_shape.start = position + offset
                    custom_shape.end = position - offset
                else:
                    offset = Position(altium_pad.topsize.x / 2 - altium_pad.topsize.y / 2)
                    custom_shape.start = position + offset
                    custom_shape.end = position - offset

                if altium_pad.direction != 0:
                    """ROTATE ELEMENT"""
                    pass

        case ALTIUM_PAD_SHAPE.OCTAGONAL:
            custom_shape = GrPoly()
            custom_shape.fill = "solid"
            custom_shape.layer = layer
            custom_shape.stroke = Stroke(0, "default")
            position = convert_altium_position(altium_pad.position)
            p11 = position + Position(altium_pad.topsize.x / 2, altium_pad.topsize.y / 2)
            p12 = position + Position(altium_pad.topsize.x / 2, -altium_pad.topsize.y / 2)
            p22 = position + Position(-altium_pad.topsize.x / 2, -altium_pad.topsize.y / 2)
            p21 = position + Position(-altium_pad.topsize.x / 2, altium_pad.topsize.y / 2)
            chamfer = min(altium_pad.topsize.x, altium_pad.topsize.y) / 4
            chamfer_x = Position(chamfer, 0)
            chamfer_y = Position(0, chamfer)
            custom_shape.coordinates = [
                p11 - chamfer_x,
                p11 - chamfer_y,
                p12 + chamfer_y,
                p12 - chamfer_x,
                p22 + chamfer_x,
                p22 + chamfer_y,
                p21 - chamfer_y,
                p21 + chamfer_x,
            ]

            if altium_pad.direction != 0:
                """ROTATE ELEMENT"""
                pass

        case _:
            raise AttributeError(f"Non-copper pad {altium_pad.name} uses an unknown shape.")

    return custom_shape
