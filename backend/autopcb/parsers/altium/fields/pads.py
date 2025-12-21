import sys
from dataclasses import dataclass, field

from construct import Container, Struct
from kicad_modification.core import CustomAutoPCBBoard, CustomAutoPCBFootprint, CustomAutoPCBPad
from kicad_modification.datatypes import Position
from kicad_modification.items import FpLine, FpPoly, GrCircle, GrLine, GrPoly
from kicad_modification.parsers.altium.constructs import ConstructPads6
from kicad_modification.parsers.altium.converters import convert_altium_position, convert_object
from kicad_modification.parsers.altium.enums import (
    ALTIUM_LAYER,
    ALTIUM_MODE,
    ALTIUM_PAD_HOLE_SHAPE,
    ALTIUM_PAD_MODE,
    KICAD_LAYER,
)
from kicad_modification.parsers.altium.utills import (
    convert_altium_pad,
    get_kicad_layer,
    is_altium_copper_layer,
    is_internal_altium_plane,
)
from kiutils.footprint import DrillDefinition
from kiutils.items.common import Net

ALTIUM_POLYGON_NONE = sys.maxsize & 0xFFFF
ALTIUM_COMPONENT_NONE = 65535
ALTIUM_POLYGON_BOARD = 65534
ALTIUM_NET_UNCONNECTED = 65535


@dataclass
class Pads6:
    data: Container | None = field(default=None)
    struct: Struct = ConstructPads6
    _kicad: CustomAutoPCBBoard | None = field(default=None)

    def update_altium_container(self, kicad_pcb: CustomAutoPCBBoard):
        pass

    def update_kicad_pcb(self, kicad_pcb: CustomAutoPCBBoard) -> CustomAutoPCBBoard:
        self._kicad = kicad_pcb
        for altium_pad in self.data.pads:
            if altium_pad.component == ALTIUM_COMPONENT_NONE:
                self.to_kicad_board_item(altium_pad)
            else:
                self.to_kicad_footprint_item(altium_pad)

        return self._kicad

    def to_kicad_footprint_item(self, altium_pad: Container):
        if (
            not is_altium_copper_layer(altium_pad.layer)
            and not is_internal_altium_plane(altium_pad.layer)
            and int(altium_pad.layer) != ALTIUM_LAYER.MULTI_LAYER.value
        ):
            self.to_kicad_footprint_item_on_non_copper(altium_pad)
        else:
            self.to_kicad_footprint_item_on_copper(altium_pad)

    def to_kicad_board_item(self, altium_pad: Container):
        if (
            not is_altium_copper_layer(altium_pad.layer)
            and not is_internal_altium_plane(altium_pad.layer)
            and int(altium_pad.layer) != ALTIUM_LAYER.MULTI_LAYER.value
        ):
            self.to_kicad_board_item_on_non_copper(altium_pad)
        else:
            # Pad can't be added directly into PCB, so place inside a footprint
            self.to_kicad_footprint_item_on_copper(altium_pad)

    def to_kicad_footprint_item_on_non_copper(self, altium_pad: Container):
        shape = convert_altium_pad(altium_pad)
        if isinstance(shape, GrPoly):
            shape = convert_object(shape, FpPoly)
        elif isinstance(shape, GrCircle):
            shape = convert_object(shape, FpPoly)
        elif isinstance(shape, GrLine):
            shape = convert_object(shape, FpLine)
        else:
            return

        self._kicad.footprints[altium_pad.component].add_fp_item(shape)

    def to_kicad_footprint_item_on_copper(self, altium_pad: Container):
        kicad_pad = CustomAutoPCBPad()
        kicad_pad.number = altium_pad.subrecord1.name.string
        if altium_pad.net != ALTIUM_NET_UNCONNECTED:
            kicad_pad.net = Net(number=altium_pad.net, name=self._kicad.nets[altium_pad.net].name)

        kicad_pad.position = Position(altium_pad.position.x, altium_pad.position.y, altium_pad.direction)
        try:
            parent_footprint_position = self._kicad.footprints[altium_pad.component].position
            kicad_pad.position.X -= parent_footprint_position.X
            kicad_pad.position.Y -= parent_footprint_position.Y
            kicad_pad.position.rotate(Position(0, 0, parent_footprint_position.rot))
        except IndexError:
            pass

        if altium_pad.holesize == 0:
            kicad_pad.type = "smd"
        else:
            kicad_pad.type = "thru_hole" if altium_pad.plated else "np_thru_hole"

            if (
                not altium_pad.size_and_shape
                or int(altium_pad.size_and_shape.holeshape) == ALTIUM_PAD_HOLE_SHAPE.ROUND.value
            ):
                kicad_pad.drill = DrillDefinition(diameter=altium_pad.holesize, width=altium_pad.holesize)
            else:
                match int(altium_pad.holeshape):
                    case ALTIUM_PAD_HOLE_SHAPE.SQUARE.value:
                        # Square drill holes not supported, default to round
                        kicad_pad.drill = DrillDefinition(diameter=altium_pad.holesize, width=altium_pad.holesize)
                    case ALTIUM_PAD_HOLE_SHAPE.SLOT.value:
                        kicad_pad.drill = DrillDefinition(oval=True)
                        if altium_pad.size_and_shape.slotrotation in [0, 180]:
                            kicad_pad.drill = DrillDefinition(
                                diameter=altium_pad.size_and_shape.slotsize, width=altium_pad.holesize
                            )
                        elif altium_pad.size_and_shape.slotrotation in [90, 270]:
                            kicad_pad.drill = DrillDefinition(
                                diameter=altium_pad.holesize, width=altium_pad.size_and_shape.slotsize
                            )
                    case _:
                        kicad_pad.drill = DrillDefinition(diameter=altium_pad.holesize, width=altium_pad.holesize)

        match int(altium_pad.padmode):
            case ALTIUM_PAD_MODE.SIMPLE.value:
                kicad_pad.size = convert_altium_position(altium_pad.topsize)

        match int(altium_pad.layer):
            case ALTIUM_LAYER.TOP_LAYER.value:
                kicad_pad.layers = ["F.Cu", "F.Paste", "F.Mask"]
            case ALTIUM_LAYER.BOTTOM_LAYER.value:
                kicad_pad.layers = ["B.Cu", "B.Paste", "B.Mask"]
            case ALTIUM_LAYER.MULTI_LAYER.value:
                kicad_pad.layers = ["F.Cu", "F.Paste", "F.Mask"] if altium_pad.plated else ["F.Cu", "F.Paste", "F.Mask"]
            case _:
                kicad_pad.layers = [get_kicad_layer(altium_pad.layer).name]

        if altium_pad.pastemaskexpansionmode == ALTIUM_MODE.MANUAL:
            kicad_pad.solderPasteMargin = altium_pad.pastemaskexpansionmanual
        if altium_pad.soldermaskexpansionmode == ALTIUM_MODE.MANUAL:
            kicad_pad.solderMaskMargin = altium_pad.soldermaskexpansionmanual
        if altium_pad.is_tent_top:
            kicad_pad.layers = ["F.Mask"]
        if altium_pad.is_tent_bottom:
            kicad_pad.layers = ["B.Mask"]

        if int(altium_pad.component) == ALTIUM_COMPONENT_NONE:
            footprint = CustomAutoPCBFootprint()
            footprint.pads.append(kicad_pad)
            self._kicad.footprints.append(footprint)
        else:
            self._kicad.footprints[altium_pad.component].pads.append(kicad_pad)

    def to_kicad_board_item_on_non_copper(self, altium_pad: Container):
        kicad_layer = get_kicad_layer(altium_pad.layer)
        if kicad_layer == KICAD_LAYER.Undefined_Layer:
            kicad_layer = KICAD_LAYER.Eco1_User

        shape = convert_altium_pad(altium_pad)
        if shape is not None:
            self._kicad.add_gr_item(shape)
