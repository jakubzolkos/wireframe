from dataclasses import dataclass, field

from construct import Container, Struct
from kicad_modification.core import CustomAutoPCBBoard, CustomAutoPCBPad
from kicad_modification.datatypes import Position
from kicad_modification.items import FpRect, GrPoly, GrRect, Zone
from kicad_modification.parsers.altium.constructs import ConstructFills6
from kicad_modification.parsers.altium.converters import convert_altium_position
from kicad_modification.parsers.altium.enums import ALTIUM_LAYER, KICAD_LAYER
from kicad_modification.parsers.altium.utills import (
    get_kicad_layer,
    get_kicad_layers_to_iterate,
    is_altium_copper_layer,
)
from kiutils.footprint import PadOptions
from kiutils.items.common import Stroke
from kiutils.items.zones import KeepoutSettings

ALTIUM_COMPONENT_NONE = 65535
ALTIUM_POLYGON_BOARD = 65534
ALTIUM_NET_UNCONNECTED = 65535


@dataclass
class Fills6:
    data: Container | None = field(default=None)
    struct: Struct = ConstructFills6
    _kicad: CustomAutoPCBBoard | None = field(default=None)

    """ DONE """

    def update_altium_container(self, kicad_pcb: CustomAutoPCBBoard):
        pass

    def update_kicad_pcb(self, kicad_pcb: CustomAutoPCBBoard) -> CustomAutoPCBBoard:
        self._kicad = kicad_pcb
        for altium_fill in self.data.fills:
            if altium_fill.component == ALTIUM_COMPONENT_NONE:
                self.to_kicad_board_item(altium_fill)
            else:
                self.to_kicad_footprint_item(altium_fill)

        return self._kicad

    def to_kicad_board_item(self, altium_fill: Container):
        if altium_fill.is_keepout or int(altium_fill.layer) == ALTIUM_LAYER.KEEP_OUT_LAYER.value:
            shape = FpRect()
            pos1 = convert_altium_position(altium_fill.pos1)
            pos2 = convert_altium_position(altium_fill.pos2)
            shape.start = pos1
            shape.end = pos2
            shape.stroke = Stroke(0, "solid")
            if altium_fill.rotation != 0:
                center = (pos1 + pos2) / 2
                shape.start.rotate(center)
                shape.end.rotate(center)

            keepout_zone = Zone()
            keepout_zone.priority = 0
            keepout_zone.layers.append(get_kicad_layer(altium_fill.layer).name)

            restrictions = altium_fill.keepoutrestrictions.value
            set_restriction = lambda restricted: "not_allowed" if restricted else "allowed"
            keepout_zone.keepoutSettings = KeepoutSettings(
                vias=set_restriction((restrictions & 0x01) != 0),
                tracks=set_restriction((restrictions & 0x02) != 0),
                copperpour=set_restriction((restrictions & 0x04) != 0),
                pads=set_restriction((restrictions & 0x08) != 0 and (restrictions & 0x10) != 0),
                footprints="not_allowed",
            )
            self._kicad.zones.append(keepout_zone)
        else:
            for layer in get_kicad_layers_to_iterate(altium_fill.layer):
                self.to_kicad_board_item_on_layer(altium_fill, layer)

    def to_kicad_footprint_item(self, altium_fill: Container):
        if altium_fill.is_keepout or int(altium_fill.layer) == ALTIUM_LAYER.KEEP_OUT_LAYER.value:
            shape = FpRect()
            pos1 = convert_altium_position(altium_fill.pos1)
            pos2 = convert_altium_position(altium_fill.pos2)
            shape.start = pos1
            shape.end = pos2
            shape.stroke = Stroke(0, "solid")
            if altium_fill.rotation != 0:
                center = (pos1 + pos2) / 2
                shape.start.rotate(center)
                shape.end.rotate(center)

            footprint_zone = Zone()
            footprint_zone.priority = 0
            footprint_zone.layers.append(get_kicad_layer(altium_fill.layer).name)

            restrictions = altium_fill.keepoutrestrictions.value
            set_restriction = lambda restricted: "not_allowed" if restricted else "allowed"
            footprint_zone.keepoutSettings = KeepoutSettings(
                vias=set_restriction((restrictions & 0x01) != 0),
                tracks=set_restriction((restrictions & 0x02) != 0),
                copperpour=set_restriction((restrictions & 0x04) != 0),
                pads=set_restriction((restrictions & 0x08) != 0 and (restrictions & 0x10) != 0),
                footprints="not_allowed",
            )

            try:
                parent_footprint_position = self._kicad.footprints[altium_fill.component].position
                shape.start -= parent_footprint_position
                shape.end -= parent_footprint_position
                shape.start.rotate(Position(0, 0, parent_footprint_position.rot))
                shape.end.rotate(Position(0, 0, parent_footprint_position.rot))
            except IndexError:
                pass

            self._kicad.footprints[altium_fill.component].zones.append(footprint_zone)

        elif is_altium_copper_layer(altium_fill.layer) and altium_fill.net != ALTIUM_NET_UNCONNECTED:
            for layer in get_kicad_layers_to_iterate(altium_fill.layer):
                return self.to_kicad_board_item_on_layer(altium_fill, layer)
        else:
            for layer in get_kicad_layers_to_iterate(altium_fill.layer):
                return self.to_kicad_footprint_item_on_layer(altium_fill, layer)

    def to_kicad_board_item_on_layer(self, altium_fill: Container, layer: KICAD_LAYER):
        shape = GrRect()
        shape.start = convert_altium_position(altium_fill.pos1)
        shape.end = convert_altium_position(altium_fill.pos2)
        shape.layer = layer.name

        if is_altium_copper_layer(altium_fill.layer) and altium_fill.net != ALTIUM_NET_UNCONNECTED:
            """TO DO: Board graphic items are supposed to have net code attribute: altium_pcb.cpp line 4687"""
            pass

        if altium_fill.rotation != 0:
            pos1 = convert_altium_position(altium_fill.pos1)
            pos2 = convert_altium_position(altium_fill.pos2)
            center = (pos1 + pos2) / 2
            shape.start.rotate(center)
            shape.end.rotate(center)

        self._kicad.add_gr_item(shape)

    def to_kicad_footprint_item_on_layer(self, altium_fill: Container, layer: KICAD_LAYER):
        pos1 = convert_altium_position(altium_fill.pos1)
        pos2 = convert_altium_position(altium_fill.pos2)

        if layer == KICAD_LAYER.F_Cu or layer == KICAD_LAYER.B_Cu:
            pad = CustomAutoPCBPad()
            pad.layers = [layer.name]
            pad.type = "smd"
            width = abs(pos2.X - pos1.X)
            height = abs(pos2.Y - pos1.Y)

            if altium_fill.rotation % 90 == 0:
                pad.shape = "rect"
                if altium_fill.rotation == 90 or altium_fill.rotation == 270:
                    width, height = height, width
                pad.size = Position(width, height)
                pad.position = (pos1 + pos2) / 2
            else:
                pad.shape = "custom"
                anchor_size = min(width, height)
                anchor_pos = pos1
                pad.customPadOptions = PadOptions(anchor="circle")
                pad.size = Position(anchor_size, anchor_size)
                pad.position = anchor_pos

                custom_primitive_poly = GrPoly()
                custom_primitive_poly.layer = layer.name
                custom_primitive_poly.coordinates = [
                    Position(pos1.X - anchor_pos.X, pos1.Y - anchor_pos.Y),
                    Position(pos2.X - anchor_pos.X, pos1.Y - anchor_pos.Y),
                    Position(pos2.X - anchor_pos.X, pos2.Y - anchor_pos.Y),
                    Position(pos1.X - anchor_pos.X, pos2.Y - anchor_pos.Y),
                ]

                if altium_fill.rotation != 0:
                    center = (pos1 + pos2) / 2
                    center.rot = altium_fill.rotation
                    for index, vertex in enumerate(custom_primitive_poly.coordinates):
                        custom_primitive_poly.coordinates[index].rotate(center)

                pad.customPadPrimitives.append(custom_primitive_poly)

            try:
                parent_footprint_position = self._kicad.footprints[altium_fill.component].position
                pad.position -= parent_footprint_position
            except IndexError:
                pass

            self._kicad.footprints[altium_fill.component].pads.append(pad)

        else:
            shape = FpRect(
                layer=layer.name,
                start=convert_altium_position(altium_fill.pos1),
                end=convert_altium_position(altium_fill.pos2),
                stroke=Stroke(width=0),
            )

            if altium_fill.rotation != 0:
                center = (pos1 + pos2) / 2
                center.rot = altium_fill.rotation
                shape.start.rotate(center)
                shape.end.rotate(center)

            try:
                parent_footprint_position = self._kicad.footprints[altium_fill.component].position
                shape.start -= parent_footprint_position
                shape.end -= parent_footprint_position
                shape.start.rotate(Position(0, 0, parent_footprint_position.rot))
                shape.end.rotate(Position(0, 0, parent_footprint_position.rot))
            except IndexError:
                pass

            self._kicad.footprints[altium_fill.component].add_fp_item(shape)
