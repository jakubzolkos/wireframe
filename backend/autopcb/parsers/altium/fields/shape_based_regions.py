import sys
from dataclasses import dataclass, field

from construct import Container, Struct
from kicad_modification.core import CustomAutoPCBBoard, CustomAutoPCBPad
from kicad_modification.datatypes import Position
from kicad_modification.items import Arc, FpPoly, GrPoly, Zone, ZonePolygon
from kicad_modification.parsers.altium.constructs import ConstructRegions6
from kicad_modification.parsers.altium.enums import ALTIUM_REGION_KIND, KICAD_LAYER
from kicad_modification.parsers.altium.utills import (
    get_board_outline,
    get_kicad_layer,
    get_kicad_layers_to_iterate,
    get_shape_line_chain_from_altium_vertices,
    is_altium_copper_layer,
)
from kiutils.footprint import PadOptions
from kiutils.items.common import Stroke
from kiutils.items.zones import Hatch, KeepoutSettings

ALTIUM_POLYGON_NONE = sys.maxsize & 0xFFFF
ALTIUM_COMPONENT_NONE = 65535
ALTIUM_POLYGON_BOARD = 65534
ALTIUM_NET_UNCONNECTED = 65535


@dataclass
class ShapeBasedRegions6:
    data: Container | None = field(default=None)
    struct: Struct = ConstructRegions6(extendedvert=True)
    _kicad: CustomAutoPCBBoard | None = field(default=None)

    def update_kicad_pcb(self, kicad_pcb: CustomAutoPCBBoard) -> CustomAutoPCBBoard:
        self._kicad = kicad_pcb
        for altium_region in self.data.regions:
            if (
                altium_region.component == ALTIUM_COMPONENT_NONE
                or int(altium_region.kind)
                or ALTIUM_REGION_KIND.BOARD_CUTOUT.value
            ):
                self.to_kicad_board_item(altium_region)
            else:
                self.to_kicad_footprint_item(altium_region)

        return self._kicad

    def to_kicad_board_item(self, altium_region: Container):
        kind = ALTIUM_REGION_KIND(int(altium_region.kind))

        if kind == ALTIUM_REGION_KIND.BOARD_CUTOUT:
            board_outline = get_board_outline(altium_region.outline)
            for elem in board_outline:
                self._kicad_pcb.add_gr_item(elem)

        elif kind == ALTIUM_REGION_KIND.POLYGON_CUTOUT or altium_region.is_keepout:
            linechain = get_shape_line_chain_from_altium_vertices(altium_region.outline)
            if len(linechain) < 3:
                return

            zone = Zone()
            zone.hatch = Hatch("edge", 0.5)
            zone.polygons = [ZonePolygon(coordinates=linechain)]
            zone.priority = 0

            for layer in get_kicad_layers_to_iterate(altium_region.layer):
                zone.layers.append(layer.name)

            if kind == ALTIUM_REGION_KIND.POLYGON_CUTOUT:
                zone.keepoutSettings = KeepoutSettings(
                    copperpour="not_allowed",
                    vias="allowed",
                    tracks="allowed",
                    pads="allowed",
                    footprints="allowed",
                )
            elif altium_region.is_keepout:
                restrictions = altium_region.keepoutrestrictions.value
                set_restriction = lambda restricted: "not_allowed" if restricted else "allowed"
                zone.keepoutSettings = KeepoutSettings(
                    vias=set_restriction((restrictions & 0x01) != 0),
                    tracks=set_restriction((restrictions & 0x02) != 0),
                    copperpour=set_restriction((restrictions & 0x04) != 0),
                    pads=set_restriction((restrictions & 0x08) != 0 and (restrictions & 0x10) != 0),
                    footprints="not_allowed",
                )

            self._kicad.zones.append(zone)

        elif kind == ALTIUM_REGION_KIND.DASHED_OUTLINE:
            layer = get_kicad_layer(altium_region.layer)
            if layer == KICAD_LAYER.Undefined_Layer:
                layer = KICAD_LAYER.Eco1_User

            linechain = get_shape_line_chain_from_altium_vertices(altium_region.outline)
            if len(linechain) < 3:
                return

            shape = GrPoly()
            shape.fill = "none"
            shape.layer = layer.name
            shape.coordinates = linechain
            shape.stroke = Stroke(0.12, "dash")

            self._kicad.add_gr_item(shape)

        elif kind == ALTIUM_REGION_KIND.COPPER:
            if altium_region.polygon == ALTIUM_POLYGON_NONE:
                for layer in get_kicad_layers_to_iterate(altium_region.layer):
                    self.to_kicad_footprint_item_on_layer(altium_region, layer)

        elif kind == ALTIUM_REGION_KIND.BOARD_CUTOUT:
            self.to_kicad_board_item_on_layer(altium_region, KICAD_LAYER.Edge_Cuts)

    def to_kicad_footprint_item(self, altium_region: Container):
        kind = ALTIUM_REGION_KIND(int(altium_region.kind))
        if kind == ALTIUM_REGION_KIND.POLYGON_CUTOUT or altium_region.is_keepout:
            linechain = get_shape_line_chain_from_altium_vertices(altium_region.outline)
            if len(linechain) < 3:
                return

            zone = Zone()
            zone.priority = 0

            if altium_region.is_keepout:
                restrictions = altium_region.keepoutrestrictions.value
                set_restriction = lambda restricted: "not_allowed" if restricted else "allowed"
                zone.keepoutSettings = KeepoutSettings(
                    vias=set_restriction((restrictions & 0x01) != 0),
                    tracks=set_restriction((restrictions & 0x02) != 0),
                    copperpour=set_restriction((restrictions & 0x04) != 0),
                    pads=set_restriction((restrictions & 0x08) != 0 and (restrictions & 0x10) != 0),
                    footprints="not_allowed",
                )
            elif kind == ALTIUM_REGION_KIND.POLYGON_CUTOUT:
                zone.keepoutSettings = KeepoutSettings(
                    copperpour="not_allowed",
                    vias="allowed",
                    tracks="allowed",
                    pads="allowed",
                    footprints="allowed",
                )

            for layer in get_kicad_layers_to_iterate(altium_region.layer):
                zone.layers.append(layer.name)

            zone.hatch = Hatch("edge", 0.5)
            self._kicad.footprints[altium_region.component].zones.append(zone)

        elif kind == ALTIUM_REGION_KIND.COPPER:
            if altium_region.polygon == ALTIUM_POLYGON_NONE:
                for layer in get_kicad_layers_to_iterate(altium_region.layer):
                    self.to_kicad_footprint_item_on_layer(altium_region, layer)

        elif kind == ALTIUM_REGION_KIND.DASHED_OUTLINE or kind == ALTIUM_REGION_KIND.BOARD_CUTOUT:
            layer = (
                KICAD_LAYER.Edge_Cuts
                if kind == ALTIUM_REGION_KIND.BOARD_CUTOUT
                else get_kicad_layer(altium_region.layer)
            )

            if layer == KICAD_LAYER.Undefined_Layer:
                layer = KICAD_LAYER.Eco1_User

            linechain = get_shape_line_chain_from_altium_vertices(altium_region.outline)
            if len(linechain) < 3:
                return

            shape = FpPoly()
            shape.fill = "none"
            shape.layer = layer.name
            shape.coordinates = linechain

            if kind == ALTIUM_REGION_KIND.DASHED_OUTLINE:
                shape.stroke = Stroke(0.05, "dash")
            else:
                shape.stroke = Stroke(0.05, "solid")

            try:
                parent = self._kicad.footprints[altium_region.component]
                for coordinate in shape.coordinates:
                    if isinstance(coordinate, Arc):
                        coordinate.start -= parent.position
                        coordinate.mid -= parent.position
                        coordinate.end -= parent.position
                    if isinstance(coordinate, Position):
                        coordinate.X -= parent.position.X
                        coordinate.Y -= parent.position.Y
                        coordinate.rotate(Position(0, 0, parent.position.rot))

                self._kicad.footprints[altium_region.component].add_fp_item(shape)
            except IndexError:
                return
        else:
            return

    def to_kicad_board_item_on_layer(self, altium_region: Container, layer: KICAD_LAYER):
        linechain = get_shape_line_chain_from_altium_vertices(altium_region.outline)
        if len(linechain) < 3:
            return

        for hole in altium_region.holes:
            hole_linechain = get_shape_line_chain_from_altium_vertices(hole.vertices)
            if len(hole_linechain) < 3:
                continue

        shape = GrPoly()
        shape.coordinates = linechain
        shape.fill = "solid"
        shape.layer = layer.name
        shape.stroke = Stroke(0)

        if KICAD_LAYER.is_copper_layer(layer.value) and altium_region.net != ALTIUM_NET_UNCONNECTED:
            shape.net = altium_region.net

        self._kicad.add_gr_item(shape)

    def to_kicad_footprint_item_on_layer(self, altium_region: Container, layer: KICAD_LAYER):
        linechain = get_shape_line_chain_from_altium_vertices(altium_region.outline)
        if len(linechain) < 3:
            return

        for hole in altium_region.holes:
            hole_linechain = get_shape_line_chain_from_altium_vertices(hole.vertices)
            if len(hole_linechain) < 3:
                continue

        if layer == KICAD_LAYER.F_Cu or layer == KICAD_LAYER.B_Cu:
            pad = CustomAutoPCBPad()
            pad.layers = [layer.name]
            pad.type = "smd"
            pad.shape = "custom"
            pad.size = Position(1, 1)

            if isinstance(linechain[0], Arc):
                pad.position = linechain[0].start
            else:
                pad.position = linechain[0]
            try:
                parent_footprint_position = self._kicad.footprints[altium_region.component].position
                pad.position -= parent_footprint_position
            except IndexError:
                pass

            shape = GrPoly()
            shape.coordinates = linechain
            shape.fill = "solid"
            shape.layer = layer.name
            shape.stroke = Stroke(0, "solid")

            pad.customPadPrimitives.append(shape, "gr_poly")
            pad.customPadOptions = PadOptions(anchor="circle")

            if KICAD_LAYER.is_copper_layer(layer.value) and altium_region.net != ALTIUM_NET_UNCONNECTED:
                shape.net = altium_region.net

            self._kicad.add_gr_item(shape)
        else:
            shape = FpPoly()
            shape.fill = "solid"
            shape.layer = layer.name
            shape.stroke = Stroke(0, "solid")
            try:
                parent = self._kicad.footprints[altium_region.component]
                for position in linechain:
                    if isinstance(position, Arc):
                        position.start -= parent.position
                        position.mid -= parent.position
                        position.end -= parent.position
                    if isinstance(position, Position):
                        position.X -= parent.position.X
                        position.Y -= parent.position.Y
                        position.rotate(Position(0, 0, parent.position.rot))

                    shape.coordinates.append(position)

                self._kicad.footprints[altium_region.component].add_fp_item(shape)
            except IndexError:
                return

    def update_altium_container(self, kicad_pcb: CustomAutoPCBBoard):
        pass
