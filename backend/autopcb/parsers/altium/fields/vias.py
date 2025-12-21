from dataclasses import dataclass, field

from construct import Container, Struct
from kicad_modification.core import CustomAutoPCBBoard
from kicad_modification.parsers.altium.constructs import ConstructVias6
from kicad_modification.parsers.altium.enums import ALTIUM_LAYER
from kicad_modification.parsers.altium.utills import convert_altium_position, get_kicad_layer, is_altium_copper_layer
from kiutils.items.brditems import Via


@dataclass
class Vias6:
    data: Container | None = field(default=None)
    struct: Struct = ConstructVias6

    """DONE"""

    def update_kicad_pcb(self, kicad_pcb: CustomAutoPCBBoard) -> CustomAutoPCBBoard:
        for altium_via in self.data.vias:
            via = Via()
            via.position = convert_altium_position(altium_via.position)
            via.size = altium_via.diameter
            via.drill = altium_via.holesize
            via.net = altium_via.net
            via.locked = altium_via.is_locked

            start_layer = ALTIUM_LAYER(int(altium_via.layer_start))
            end_layer = ALTIUM_LAYER(int(altium_via.layer_end))

            start_layer_outside = start_layer == ALTIUM_LAYER.TOP_LAYER or start_layer == ALTIUM_LAYER.BOTTOM_LAYER
            end_layer_outside = end_layer == ALTIUM_LAYER.TOP_LAYER or end_layer == ALTIUM_LAYER.BOTTOM_LAYER

            # None indicates a throughhole via
            if start_layer_outside and end_layer_outside:
                via.type = None
            elif not start_layer_outside and not end_layer_outside:
                via.type = "blind"
            else:
                via.type = "micro"

            if not is_altium_copper_layer(start_layer) or not is_altium_copper_layer(end_layer):
                print("Via endpoint layers use a non-copper layer which is unsupported. Skipping.")

            via.layers = [
                get_kicad_layer(start_layer).name,
                get_kicad_layer(end_layer).name,
            ]
            kicad_pcb.via.append(via)

        return kicad_pcb

    def update_altium_container(self, kicad_pcb: CustomAutoPCBBoard):
        pass
