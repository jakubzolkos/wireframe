import sys
import uuid
from dataclasses import dataclass, field

from construct import Container, Struct
from kicad_modification.core import CustomAutoPCBBoard
from kicad_modification.datatypes import Position
from kicad_modification.items import FpLine, GrLine
from kicad_modification.parsers.altium.constructs import ConstructTracks6
from kicad_modification.parsers.altium.converters import convert_altium_position
from kicad_modification.parsers.altium.enums import ALTIUM_LAYER, KICAD_LAYER
from kicad_modification.parsers.altium.utills import (
    get_kicad_layer,
    get_kicad_layers_to_iterate,
    get_shape_as_keepout_region,
    is_altium_copper_layer,
    is_internal_altium_plane,
)
from kiutils.items.brditems import Segment
from kiutils.items.common import Stroke

ALTIUM_POLYGON_NONE = sys.maxsize & 0xFFFF
ALTIUM_COMPONENT_NONE = 65535
ALTIUM_POLYGON_BOARD = 65534
ALTIUM_NET_UNCONNECTED = 65535


@dataclass
class Tracks6:
    data: Container | None = field(default=None)
    struct: Struct = ConstructTracks6
    _kicad: CustomAutoPCBBoard | None = field(default=None)

    def update_altium_container(self, kicad_pcb: CustomAutoPCBBoard):
        pass

    def update_kicad_pcb(self, kicad_pcb: CustomAutoPCBBoard) -> CustomAutoPCBBoard:
        self._kicad = kicad_pcb
        for altium_track in self.data.tracks:
            if altium_track.component == ALTIUM_COMPONENT_NONE:
                self.to_kicad_board_item(altium_track)
            else:
                self.to_kicad_footprint_item(altium_track)

        return self._kicad

    def to_kicad_board_item(self, altium_track: Container):
        if altium_track.polygon != ALTIUM_POLYGON_NONE and altium_track.polygon != ALTIUM_POLYGON_BOARD:
            try:
                zone = self._kicad.zones[altium_track.polygon]
            except IndexError:
                return

            kicad_layer = get_kicad_layer(altium_track.layer)
            if kicad_layer == KICAD_LAYER.Undefined_Layer or any(
                zone.layer == kicad_layer.name for zone in self._kicad.zones
            ):
                return

        elif altium_track.is_keepout or ALTIUM_LAYER(int(altium_track.layer)) == ALTIUM_LAYER.KEEP_OUT_LAYER:
            shape = GrLine()
            shape.start = convert_altium_position(altium_track.start)
            shape.end = convert_altium_position(altium_track.end)
            zone = get_shape_as_keepout_region(altium_track, shape)
            self._kicad.zones.append(zone)

        else:
            for layer in get_kicad_layers_to_iterate(altium_track.layer):
                self.to_kicad_board_item_on_layer(altium_track, layer)

        # ITERATE THROUGH LAYER EXPANSION MASKS

    def to_kicad_footprint_item(self, altium_track: Container):
        if altium_track.polygon != ALTIUM_POLYGON_NONE:
            return

        if (
            altium_track.is_keepout
            or int(altium_track.layer) == ALTIUM_LAYER.KEEP_OUT_LAYER.value
            or is_internal_altium_plane(altium_track.layer)
        ):
            # Keepout region
            shape = FpLine()
            shape.start = convert_altium_position(altium_track.start)
            shape.end = convert_altium_position(altium_track.end)
            layer = get_kicad_layer(altium_track.layer)
            shape.layer = layer.name
            shape.width = None
            shape.stroke = Stroke(altium_track.width, "solid")
            zone = get_shape_as_keepout_region(altium_track, shape)
            self._kicad.footprints[altium_track.component].zones.append(zone)
            pass
        else:
            for layer in get_kicad_layers_to_iterate(altium_track.layer):
                if KICAD_LAYER.is_copper_layer(layer) and altium_track.net != ALTIUM_NET_UNCONNECTED:
                    self.to_kicad_board_item_on_layer(altium_track, layer)
                else:
                    self.to_kicad_footprint_item_on_layer(altium_track, layer)

        # ITERATE THROUGH LAYER EXPANSION MASKS

    def to_kicad_board_item_on_layer(self, altium_track: Container, kicad_layer: KICAD_LAYER):
        if is_altium_copper_layer(altium_track.layer) and altium_track.net != ALTIUM_NET_UNCONNECTED:
            segment = Segment()
            segment.start = convert_altium_position(altium_track.start)
            segment.end = convert_altium_position(altium_track.end)
            segment.width = altium_track.width
            segment.layer = kicad_layer.name
            segment.net = altium_track.net
            segment.tstamp = uuid.uuid4()
            self._kicad.segment.append(segment)
        else:
            shape = GrLine()
            shape.start = convert_altium_position(altium_track.start)
            shape.end = convert_altium_position(altium_track.end)
            shape.layer = kicad_layer.name
            shape.stroke = Stroke(altium_track.width, "solid")

            self._kicad.add_gr_item(shape)

    def to_kicad_footprint_item_on_layer(self, altium_track: Container, kicad_layer: KICAD_LAYER):
        shape = FpLine()
        shape.start = convert_altium_position(altium_track.start)
        shape.end = convert_altium_position(altium_track.end)
        shape.layer = kicad_layer.name
        shape.width = None
        shape.stroke = Stroke(altium_track.width, "solid")

        try:
            parent_footprint_position = self._kicad.footprints[altium_track.component].position
            shape.start -= parent_footprint_position
            shape.end -= parent_footprint_position
            shape.start.rotate(Position(0, 0, parent_footprint_position.rot))
            shape.end.rotate(Position(0, 0, parent_footprint_position.rot))
        except IndexError:
            pass

        self._kicad.footprints[altium_track.component].fp_line.append(shape)
