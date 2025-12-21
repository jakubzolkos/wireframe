import copy
import math
import sys
from dataclasses import dataclass, field

from construct import Container, Struct
from kicad_modification.core import CustomAutoPCBBoard
from kicad_modification.datatypes import Position
from kicad_modification.items import FpArc, FpCircle, GrArc, GrCircle
from kicad_modification.parsers.altium.constructs import ConstructArcs6
from kicad_modification.parsers.altium.converters import convert_altium_position, convert_object, ki_round
from kicad_modification.parsers.altium.enums import ALTIUM_LAYER, KICAD_LAYER
from kicad_modification.parsers.altium.utills import (
    get_kicad_layer,
    get_kicad_layers_to_iterate,
    get_shape_as_keepout_region,
    is_internal_altium_plane,
)
from kiutils.items.brditems import Arc
from kiutils.items.common import Stroke

ALTIUM_POLYGON_NONE = sys.maxsize & 0xFFFF
ALTIUM_COMPONENT_NONE = 65535
ALTIUM_POLYGON_BOARD = 65534
ALTIUM_NET_UNCONNECTED = 65535


def create_arc(center: Position, radius: float, start_angle: float, end_angle: float):
    """
    Calculate the start, midpoint, and end points of an arc.

    Parameters:
        center (Position): Center of the circle.
        radius (float): Radius of the circle.
        start_angle (float): Starting angle of the arc in degrees.
        end_angle (float): Ending angle of the arc in degrees.

    Returns:
        dict: A dictionary containing start, midpoint, and end points as Position objects.
    """
    angle_diff = (start_angle - end_angle) % 360
    midpoint_angle = start_angle - (angle_diff / 2)

    start_rad = math.radians(end_angle)
    mid_rad = math.radians(-midpoint_angle)
    end_rad = math.radians(start_angle)

    # Calculate start, midpoint, and end positions
    start = Position(center.X + radius * math.cos(start_rad), center.Y + radius * -math.sin(start_rad))
    mid = Position(center.X + radius * math.cos(mid_rad), center.Y + radius * -math.sin(mid_rad))
    end = Position(center.X + radius * math.cos(end_rad), center.Y + radius * -math.sin(end_rad))

    return start, mid, end


@dataclass
class Arcs6:
    data: Container | None = field(default=None)
    struct: Struct = ConstructArcs6
    _kicad: CustomAutoPCBBoard | None = field(default=None)

    def update_kicad_pcb(self, kicad_pcb: CustomAutoPCBBoard) -> CustomAutoPCBBoard:
        self._kicad = kicad_pcb
        for altium_arc in self.data.arcs:
            if altium_arc.component == ALTIUM_COMPONENT_NONE:
                self.to_kicad_board_item(altium_arc)
            else:
                self.to_kicad_footprint_item(altium_arc)

        return self._kicad

    def update_altium_container(self, kicad_pcb: CustomAutoPCBBoard):
        pass

    def to_kicad_board_item(self, altium_arc: Container) -> GrCircle | GrArc | None:
        if altium_arc.polygon != ALTIUM_POLYGON_NONE and altium_arc.polygon != ALTIUM_POLYGON_BOARD:
            zone = self._kicad.zones[altium_arc.polygon]
            zone_fills = [polygon for polygon in zone.filledPolygons if polygon.layer == layer.name]
            layer = get_kicad_layer(altium_arc.layer)

            if layer == KICAD_LAYER.Undefined_Layer or not zone_fills:
                return None

            shape = self.to_kicad_shape(altium_arc)
            shape.stroke = Stroke(
                width=altium_arc.width,
                type="solid",
            )

            zone.fillSettings(yes=False)

        if (
            altium_arc.is_keepout
            or int(altium_arc.layer) == ALTIUM_LAYER.KEEP_OUT_LAYER.value
            or is_internal_altium_plane(altium_arc.layer)
        ):
            shape = self.to_kicad_shape(altium_arc)
            zone = get_shape_as_keepout_region(altium_arc, shape)
            self._kicad.zones.append(zone)
        else:
            for layer in get_kicad_layers_to_iterate(altium_arc.layer):
                print("to board item entering board on layer")

                self.to_kicad_board_item_on_layer(altium_arc, layer)

        # ITERATE THROUGH EXPANSION MASKS

    def to_kicad_footprint_item(self, altium_arc: Container):
        if altium_arc.polygon != ALTIUM_POLYGON_NONE:
            return
        if (
            altium_arc.is_keepout
            or int(altium_arc.layer) == ALTIUM_LAYER.KEEP_OUT_LAYER.value
            or is_internal_altium_plane(altium_arc.layer)
        ):
            layer = get_kicad_layer(altium_arc.layer)
            shape = self.to_kicad_shape(altium_arc)
            zone = get_shape_as_keepout_region(altium_arc, shape)
            self._kicad.footprints[altium_arc.component].zones.append(zone)
        else:
            for layer in get_kicad_layers_to_iterate(altium_arc.layer):
                if KICAD_LAYER.is_copper_layer(layer.value) and altium_arc.net != ALTIUM_NET_UNCONNECTED:
                    self.to_kicad_board_item_on_layer(altium_arc, layer)
                else:
                    self.to_kicad_footprint_item_on_layer(altium_arc, layer)

        # ITERATE THROUGH EXPANSION MASKS

    def to_kicad_board_item_on_layer(self, altium_arc: Container, layer: KICAD_LAYER):
        if KICAD_LAYER.is_copper_layer(layer.value) and altium_arc.net != ALTIUM_NET_UNCONNECTED:
            included_angle = altium_arc.end_angle - altium_arc.start_angle
            if included_angle < 0:
                included_angle += 360
            elif included_angle >= 360:
                included_angle -= 360

            if included_angle >= 0.1:
                center = convert_altium_position(altium_arc.center)
                start, mid, end = create_arc(
                    center=center,
                    radius=altium_arc.radius,
                    start_angle=altium_arc.start_angle,
                    end_angle=altium_arc.end_angle,
                )
                trace_arc = Arc(
                    start=start,
                    mid=mid,
                    end=end,
                    width=altium_arc.width,
                    layer=layer.name,
                )
            self._kicad.arcs.append(trace_arc)

        else:
            board_item = self.to_kicad_shape(altium_arc)
            board_item.stroke = Stroke(altium_arc.width, "solid")
            board_item.layer = layer.name
            self._kicad.add_gr_item(board_item)

    def to_kicad_footprint_item_on_layer(self, altium_arc: Container, layer: KICAD_LAYER):
        shape = self.to_kicad_shape(altium_arc)
        parent = self._kicad.footprints[altium_arc.component]
        if isinstance(shape, GrCircle):
            footprint_item = convert_object(shape, FpCircle)
            footprint_item.center -= parent.position
            footprint_item.end -= parent.position
        elif isinstance(shape, GrArc):
            footprint_item = convert_object(shape, FpArc)
            footprint_item.start -= parent.position
            footprint_item.mid -= parent.position
            footprint_item.end -= parent.position

        footprint_item.layer = layer.name
        footprint_item.stroke = Stroke(altium_arc.width, "solid")
        self._kicad.footprints[altium_arc.component].add_fp_item(footprint_item)

    @staticmethod
    def to_kicad_shape(altium_arc: Container) -> GrCircle | GrArc:
        arc_center = convert_altium_position(altium_arc.center)
        if altium_arc.start_angle == 0 or altium_arc.end_angle == 360:
            arc_end = arc_center - Position(0, altium_arc.radius)
            shape = GrCircle(center=arc_center, end=arc_end)
        else:
            start, mid, end = create_arc(
                center=arc_center,
                radius=altium_arc.radius,
                start_angle=altium_arc.start_angle,
                end_angle=altium_arc.end_angle,
            )
            shape = GrArc(start=start, mid=mid, end=end)

        return shape
