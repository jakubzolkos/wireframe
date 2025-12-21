from dataclasses import dataclass, field

from construct import Container, Struct
from kicad_modification.core import CustomAutoPCBBoard, CustomAutoPCBFootprint
from kicad_modification.datatypes import Position
from kicad_modification.parsers.altium.constructs import ConstructComponents6
from kicad_modification.parsers.altium.enums import KICAD_LAYER
from kicad_modification.parsers.altium.utills import get_kicad_layer
from kiutils.items.fpitems import FpText


@dataclass
class Components6:
    data: Container | None = field(default=None)
    struct: Struct = ConstructComponents6

    """DONE"""

    def update_kicad_pcb(self, kicad_pcb: CustomAutoPCBBoard) -> CustomAutoPCBBoard:
        for component in self.data.components:
            footprint = CustomAutoPCBFootprint()
            footprint.position = Position(component.position.x, component.position.y, component.rotation)
            footprint.locked = component.locked
            footprint.libId = f"{component.sourcecomponentlibrary}:{component.pattern}"
            footprint.layer = "F.Cu" if get_kicad_layer(component.layer) == KICAD_LAYER.F_Cu else "B.Cu"
            footprint.reference = FpText(text=component.sourcedesignator)

            if all(c.isdigit() for c in component.sourcedesignator):
                footprint.reference.text = "UNK" + footprint.reference.text

            kicad_pcb.footprints.append(footprint)

        return kicad_pcb
